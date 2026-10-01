/* Small, independent controls for the bilingual legacy-page shell. */
(() => {
  const menus = document.querySelectorAll('[data-legacy-mobile-menu]');
  menus.forEach((menu) => {
    const summary = menu.querySelector('summary');
    const links = menu.querySelectorAll('a');

    menu.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && menu.open) {
        menu.open = false;
        summary?.focus();
      }
    });

    links.forEach((link) => {
      link.addEventListener('click', () => { menu.open = false; });
    });
    window.addEventListener('pagehide', () => { menu.open = false; });
  });

  // The legacy brief uses novalidate and a type=button Next control. Validate
  // only the active step before the existing inline handler collects its data.
  const form = document.getElementById('quizForm');
  const next = document.getElementById('quizNext');
  if (form && next) {
    const english = document.documentElement.lang === 'en';
    form.addEventListener('input', (event) => {
      if (event.target.matches('input, textarea, select')) {
        event.target.setCustomValidity('');
        event.target.classList.remove('error');
      }
    });
    next.addEventListener('click', (event) => {
      const step = form.querySelector('.quiz-step.active');
      if (!step) return;
      for (const field of step.querySelectorAll('input, textarea, select')) {
        if (!field.willValidate) continue;
        if (field.required && !field.value.trim()) {
          field.setCustomValidity(english ? 'Please complete this field.' : 'Συμπλήρωσε αυτό το πεδίο.');
        }
        if (!field.reportValidity()) {
          field.classList.add('error');
          event.preventDefault();
          event.stopImmediatePropagation();
          return;
        }
      }
    }, true);
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      if (!next.disabled) next.click();
    });
  }
})();