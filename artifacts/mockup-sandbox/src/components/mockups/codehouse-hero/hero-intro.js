/* The intro covers the existing hero; it never replaces, seeks, or reloads video. */
export function mountHeroIntro(hero) {
  const root = document.documentElement;
  if (!hero.hasAttribute('data-hero-intro')) return () => {};
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  if (reduced.matches || location.hash || !root.classList.contains('intro-pending')) {
    root.classList.remove('intro-pending');
    hero.dataset.introState = 'entered';
    return () => {};
  }
  const greek = hero.dataset.introLang !== 'en';
  let loader = document.querySelector('[data-hero-intro-loader]');
  if (!loader) {
    loader = document.createElement('div');
    loader.className = 'hero-loading-screen';
    loader.dataset.heroIntroLoader = '';
    loader.setAttribute('role', 'dialog');
    loader.setAttribute('aria-modal', 'true');
    loader.setAttribute('aria-labelledby', 'hero-intro-label');
    loader.innerHTML = `<div class="hero-intro-panel"><div class="hero-intro-caption"><span id="hero-intro-label">LOADING</span><span data-intro-percent aria-hidden="true">00%</span></div><div class="hero-intro-bar" role="progressbar" aria-label="${greek ? 'Προετοιμασία του site' : 'Preparing the site'}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0"><span data-intro-fill></span></div><button type="button" data-intro-skip>${greek ? 'ΕΙΣΟΔΟΣ ΣΤΟ SITE' : 'ENTER THE SITE'} ↗</button></div>`;
    document.body.append(loader);
  }
  const bar = loader.querySelector('[role="progressbar"]');
  const fill = loader.querySelector('[data-intro-fill]');
  const percent = loader.querySelector('[data-intro-percent]');
  const skip = loader.querySelector('[data-intro-skip]');
  const locked = [...document.body.children]
    .filter(element => element !== loader && !['SCRIPT', 'STYLE', 'LINK'].includes(element.tagName))
    .map(element => [element, element.inert]);
  locked.forEach(([element]) => { element.inert = true; });
  hero.dataset.introState = 'loading';
  let fontsReady = false, logoReady = false, done = false, frame = 0;
  let elapsed = 0, previous = performance.now(), lastPercent = -1;
  const oldBusy = root.getAttribute('aria-busy');
  root.setAttribute('aria-busy', 'true');
  skip.focus({ preventScroll: true });
  document.fonts.ready.then(() => { fontsReady = true; });
  const logo = hero.querySelector('.hero-logo');
  if (!logo || (logo.complete && logo.naturalWidth)) logoReady = true;
  else {
    // The site must remain usable even if a decorative image fails.
    logo.decode().catch(() => {}).finally(() => { logoReady = true; });
  }
  function progress(value) {
    const number = Math.max(lastPercent, Math.min(100, Math.floor(value)));
    if (number === lastPercent) return;
    lastPercent = number;
    bar.setAttribute('aria-valuenow', String(number));
    fill.style.transform = `scaleX(${number / 100})`;
    percent.textContent = `${String(number).padStart(2, '0')}%`;
  }
  function release() {
    root.classList.remove('intro-pending', 'intro-leaving');
    if (oldBusy === null) root.removeAttribute('aria-busy');
    else root.setAttribute('aria-busy', oldBusy);
    locked.forEach(([element, inert]) => { element.inert = inert; });
  }
  function finish(reason = 'ready', immediate = false) {
    if (done) return;
    done = true;
    cancelAnimationFrame(frame);
    clearTimeout(deadline);
    document.removeEventListener('keydown', onKey);
    reduced.removeEventListener('change', onReduced);
    skip.removeEventListener('click', onSkip);
    const restoreFocus = loader.contains(document.activeElement);
    // Record the handoff without changing the player's state.
    const video = hero.querySelector('.hero-video.is-active');
    hero.dataset.introExitTime = String(video?.currentTime || 0);
    hero.dataset.introExitIndex = hero.dataset.videoIndex || '0';
    hero.dataset.introState = 'entered';
    hero.dataset.introReason = reason;
    progress(100);
    root.classList.add('intro-leaving');
    release();
    loader.classList.add('is-leaving');
    if (restoreFocus) document.querySelector('.site-header a, .legacy-editorial-header a')?.focus({ preventScroll: true });
    const remove = () => loader.remove();
    if (immediate) remove();
    else setTimeout(remove, 450);
  }
  const onSkip = () => finish('skipped');
  const onKey = event => {
    if (event.key === 'Escape') { event.preventDefault(); finish('skipped'); }
    if (event.key === 'Tab') {
      event.preventDefault();
      skip.focus({ preventScroll: true });
    }
  };
  const onReduced = event => { if (event.matches) finish('reduced-motion', true); };
  const deadline = setTimeout(() => finish('timeout'), 9000);
  skip.addEventListener('click', onSkip);
  document.addEventListener('keydown', onKey);
  reduced.addEventListener('change', onReduced);
  function tick(now) {
    if (done) return;
    if (!root.classList.contains('intro-pending')) return finish('watchdog');
    const bounds = hero.getBoundingClientRect();
    if (bounds.bottom <= 0 || bounds.top >= innerHeight) return finish('restored-scroll');
    const video = hero.querySelector('.hero-video.is-active');
    const playing = video?.readyState >= 2 && !video.paused && video.currentTime > 0;
    if (playing && !document.hidden) elapsed += Math.min(100, Math.max(0, now - previous));
    previous = now;
    const readiness = (Number(fontsReady) + Number(logoReady) + Number(playing)) / 3;
    progress(Math.min(99, readiness * 35 + Math.min(1, elapsed / 2600) * 65));
    if (video?.error) return finish('video-unavailable');
    if (hero.querySelector('[data-video-toggle]')?.getAttribute('aria-pressed') === 'true') return finish('autoplay-blocked');
    if (fontsReady && logoReady && playing && elapsed >= 2600) return finish();
    frame = requestAnimationFrame(tick);
  }
  frame = requestAnimationFrame(tick);
  return () => {
    if (!done) finish('disposed', true);
    else loader.remove();
  };
}