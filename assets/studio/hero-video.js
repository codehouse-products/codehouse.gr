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
  const controls = hero.querySelector('.hero-video-controls');
  const toggle = hero.querySelector('[data-video-toggle]');
  const prev = hero.querySelector('[data-video-prev]');
  const next = hero.querySelector('[data-video-next]');
  const position = hero.querySelector('[data-video-position]');
  const status = hero.querySelector('[data-video-status]');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let index = 0, slot = 0, moving = false, disposed = false, inView = true;
  let userPaused = reduced.matches;
  videos.forEach(video => { video.muted = true; });
  controls.hidden = false;
  const active = () => videos[slot];
  const shouldPlay = () => !userPaused && inView && !document.hidden;
  function syncButton() {
    toggle.setAttribute('aria-label', userPaused ? hero.dataset.playLabel : hero.dataset.pauseLabel);
    toggle.setAttribute('aria-pressed', String(userPaused));
    toggle.firstElementChild.textContent = userPaused ? '▶' : 'Ⅱ';
  }
  function fail() {
    status.textContent = hero.dataset.errorLabel;
    status.hidden = false;
  }
  async function resume() {
    if (!shouldPlay() || disposed) return active().pause();
    try { await active().play(); }
    catch (error) {
      if (error.name === 'NotAllowedError') { userPaused = true; syncButton(); }
      else if (error.name !== 'AbortError') fail();
    }
  }
  function prepareNext() {
    if (moving || disposed || userPaused) return;
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
    prev.disabled = next.disabled = true;
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
      prev.disabled = next.disabled = false;
      if (!disposed) prepareNext();
    }
  }
  const onPrev = () => select(index - 1);
  const onNext = () => select(index + 1);
  const onToggle = () => {
    userPaused = !userPaused;
    syncButton();
    if (userPaused) active().pause();
    else {
      if (active().ended) active().currentTime = 0;
      resume();
    }
  };
  const onEnded = event => {
    if (event.target === active() && shouldPlay()) select(index + 1);
  };
  const onVisibility = () => { shouldPlay() ? resume() : active().pause(); };
  const onReduced = event => {
    if (event.matches) { userPaused = true; active().pause(); syncButton(); }
  };
  prev.addEventListener('click', onPrev);
  next.addEventListener('click', onNext);
  toggle.addEventListener('click', onToggle);
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
  syncButton();
  const cleanupIntro = mountHeroIntro(hero);
  if (!userPaused) {
    resume().then(() => { if (!disposed && shouldPlay()) prepareNext(); });
  }
  const cleanup = () => {
    disposed = true;
    cleanupIntro();
    hero.classList.remove('hero-video-inview');
    observer.disconnect();
    videos.forEach(video => { video.pause(); video.removeEventListener('ended', onEnded); });
    prev.removeEventListener('click', onPrev);
    next.removeEventListener('click', onNext);
    toggle.removeEventListener('click', onToggle);
    document.removeEventListener('visibilitychange', onVisibility);
    reduced.removeEventListener('change', onReduced);
    mounted.delete(hero);
  };
  mounted.set(hero, cleanup);
  return cleanup;
}

document.querySelectorAll('[data-hero-autoinit]').forEach(mountHeroVideo);