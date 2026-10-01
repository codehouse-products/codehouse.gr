(() => {
  document.querySelectorAll('[data-project-gallery]').forEach(gallery => {
    const images = [...gallery.querySelectorAll('[data-gallery-slide]')];
    const controls = gallery.querySelector('.project-gallery-controls');
    const buttons = [...gallery.querySelectorAll('[data-gallery-direction]')];
    const position = gallery.querySelector('[data-gallery-position]');
    const status = gallery.querySelector('[data-gallery-status]');
    if (images.length < 2) return;

    let current = 0;
    let loading = false;
    gallery.dataset.galleryIndex = '0';
    controls.hidden = false;

    async function show(index) {
      if (loading) return;
      const next = (index + images.length) % images.length;
      if (next === current) return;
      const focusedButton = buttons.includes(document.activeElement) ? document.activeElement : null;
      loading = true;
      gallery.setAttribute('aria-busy', 'true');
      buttons.forEach(button => { button.disabled = true; });
      status.hidden = true;
      try {
        const image = images[next];
        image.loading = 'eager';
        if (image.complete && image.naturalWidth === 0) {
          image.src = image.getAttribute('src');
        }
        // Decode first so a slow connection does not replace the photo with a blank frame.
        await image.decode();
        images[current].hidden = true;
        image.hidden = false;
        current = next;
        gallery.dataset.galleryIndex = String(current);
        position.textContent = `${String(current + 1).padStart(2, '0')} / ${String(images.length).padStart(2, '0')}`;
      } catch {
        status.textContent = gallery.dataset.galleryError;
        status.hidden = false;
      } finally {
        loading = false;
        gallery.removeAttribute('aria-busy');
        buttons.forEach(button => { button.disabled = false; });
        // Disabling a focused control moves focus to body in Chromium. Restore
        // it only if the visitor has not moved elsewhere during image loading.
        if (focusedButton && document.activeElement === document.body) {
          focusedButton.focus({ preventScroll: true });
        }
      }
    }

    buttons.forEach(button => {
      button.addEventListener('click', () => {
        show(current + (button.dataset.galleryDirection === 'next' ? 1 : -1));
      });
    });

    gallery.addEventListener('keydown', event => {
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') return;
      event.preventDefault();
      // Gallery keys must not also move the surrounding projects rail.
      event.stopPropagation();
      show(current + (event.key === 'ArrowRight' ? 1 : -1));
    });
  });
})();