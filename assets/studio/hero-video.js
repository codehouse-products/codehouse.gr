import { mountHeroIntro } from './hero-intro.js';

const mounted = new WeakMap();

export function mountHeroVideo(hero) {
  if (!hero) return () => {};
  if (mounted.has(hero)) return mounted.get(hero);
  const videos = [...hero.querySelectorAll('.hero-video')];
  const clips = JSON.parse(hero.dataset.playlist).map(clip => ({
    ...clip,
    src: videos[0].canPlayType('video/webm; codecs="vp9"') ? clip.webm : clip.src,
  }));
  if (videos[0].getAttribute('src') !== clips[0].src) {
    videos[0].src = clips[0].src;
    videos[0].load();
  }
  const info = hero.querySelector('.hero-video-info');
  const position = hero.querySelector('[data-video-position]');
  const status = hero.querySelector('[data-video-status]');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let index = 0, slot = 0, moving = false, disposed = false, inView = true;
  let playbackBlocked = false;
  hero.dataset.videoAutoplayBlocked = 'false';
  videos.forEach(video => { video.muted = true; });
  info.hidden = false;
  const active = () => videos[slot];
  const shouldPlay = () => !reduced.matches && !playbackBlocked && inView && !document.hidden;
  function fail() {
    status.textContent = hero.dataset.errorLabel;
    status.hidden = false;
  }
  async function resume() {
    if (!shouldPlay() || disposed) return active().pause();
    try { await active().play(); }
    catch (error) {
      if (error.name === 'NotAllowedError') {
        playbackBlocked = true;
        hero.dataset.videoAutoplayBlocked = 'true';
      }
      else if (error.name !== 'AbortError') fail();
    }
  }
  function prepareNext() {
    if (moving || disposed || reduced.matches || playbackBlocked) return;
    const video = videos[1 - slot], clip = clips[(index + 1) % clips.length];
    if (video.getAttribute('src') !== clip.src) {
      video.pause();
      video.src = clip.src;
      video.poster = clip.poster;
      video.preload = 'auto';
      video.load();
    }
  }
  function ready(video) {
    if (video.readyState >= 2) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => finish(new Error('Video timeout')), 15000);
      function finish(error) {
        clearTimeout(timer);
        video.removeEventListener('loadeddata', loaded);
        video.removeEventListener('error', failed);
        error ? reject(error) : resolve();
      }
      const loaded = () => finish();
      const failed = () => finish(new Error('Video unavailable'));
      video.addEventListener('loadeddata', loaded, { once: true });
      video.addEventListener('error', failed, { once: true });
    });
  }
  async function select(target) {
    if (moving || disposed) return;
    const selected = (target + clips.length) % clips.length;
    if (selected === index) return;
    moving = true;
    status.hidden = true;
    const incoming = videos[1 - slot], clip = clips[selected];
    try {
      if (incoming.getAttribute('src') !== clip.src || incoming.error) {
        incoming.src = clip.src;
        incoming.poster = clip.poster;
        incoming.preload = 'auto';
        incoming.load();
      }
      await ready(incoming);
      if (disposed) return;
      incoming.currentTime = 0;
      active().pause();
      active().classList.remove('is-active');
      slot = 1 - slot;
      index = selected;
      active().classList.add('is-active');
      hero.dataset.videoIndex = String(index);
      position.textContent = `${String(index + 1).padStart(2, '0')} / ${String(clips.length).padStart(2, '0')} — ${clip.label}`;
      await resume();
    } catch { if (!disposed) fail(); }
    finally {
      moving = false;
      if (!disposed) prepareNext();
    }
  }
  const onEnded = event => {
    if (event.target === active() && shouldPlay()) select(index + 1);
  };
  const onVisibility = () => { shouldPlay() ? resume() : active().pause(); };
  const onReduced = () => {
    onVisibility();
    if (!reduced.matches) prepareNext();
  };
  // Muted inline playback normally autostarts. If a browser blocks it,
  // retry on a normal page interaction without adding video controls.
  const onGesture = () => {
    if (!playbackBlocked || reduced.matches) return;
    playbackBlocked = false;
    hero.dataset.videoAutoplayBlocked = 'false';
    resume().then(() => { if (!disposed && shouldPlay()) prepareNext(); });
  };
  document.addEventListener('pointerdown', onGesture);
  document.addEventListener('keydown', onGesture);
  videos.forEach(video => video.addEventListener('ended', onEnded));
  document.addEventListener('visibilitychange', onVisibility);
  reduced.addEventListener('change', onReduced);
  const observer = new IntersectionObserver(entries => {
    inView = entries[0].isIntersecting && entries[0].intersectionRatio >= .15;
    hero.classList.toggle('hero-video-inview', inView);
    onVisibility();
  }, { threshold: .15 });
  observer.observe(hero);
  hero.dataset.videoIndex = '0';
  const cleanupIntro = mountHeroIntro(hero);
  if (!reduced.matches) {
    resume().then(() => { if (!disposed && shouldPlay()) prepareNext(); });
  }
  const cleanup = () => {
    disposed = true;
    cleanupIntro();
    hero.classList.remove('hero-video-inview');
    observer.disconnect();
    videos.forEach(video => { video.pause(); video.removeEventListener('ended', onEnded); });
    document.removeEventListener('pointerdown', onGesture);
    document.removeEventListener('keydown', onGesture);
    document.removeEventListener('visibilitychange', onVisibility);
    reduced.removeEventListener('change', onReduced);
    mounted.delete(hero);
    delete hero.dataset.videoAutoplayBlocked;
  };
  mounted.set(hero, cleanup);
  return cleanup;
}

document.querySelectorAll('[data-hero-autoinit]').forEach(mountHeroVideo);