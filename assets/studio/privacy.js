/* Preserve existing GA4/Clarity integrations without loading them before consent.
   Measurement/project IDs below are public identifiers, not credentials. */
(() => {
  const english = document.documentElement.lang === 'en';
  let consent = null;
  let started = false;
  try { consent = localStorage.getItem('cookieConsent'); } catch {}

  function enableMeasurement() {
    if (started) return;
    started = true;
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('consent', 'update', {
      analytics_storage: 'granted',
      ad_storage: 'denied',
      ad_user_data: 'denied',
      ad_personalization: 'denied'
    });
    window.gtag('config', 'G-G9JE7KSR99', {
      anonymize_ip: true,
      page_path: location.pathname,
      allow_google_signals: false,
      allow_ad_personalization_signals: false
    });
    const google = document.createElement('script');
    google.async = true;
    google.src = 'https://www.googletagmanager.com/gtag/js?id=G-G9JE7KSR99';
    document.head.appendChild(google);
    window.clarity = window.clarity || function () {
      (window.clarity.q = window.clarity.q || []).push(arguments);
    };
    const clarity = document.createElement('script');
    clarity.async = true;
    clarity.src = 'https://www.clarity.ms/tag/p9o7k2u3x5';
    document.head.appendChild(clarity);
  }

  function choose(value) {
    consent = value;
    try { localStorage.setItem('cookieConsent', value); } catch {}
    document.querySelector('.studio-consent')?.remove();
    if (value === 'accepted') enableMeasurement();
    // Reload on revocation to remove both already-loaded third-party trackers.
    // The stored rejected choice prevents them loading on the fresh page.
    else if (started) location.reload();
  }

  function showChoices() {
    if (document.querySelector('.studio-consent')) return;
    const banner = document.createElement('section');
    banner.className = 'studio-consent';
    banner.setAttribute('aria-label', english ? 'Privacy choices' : 'Επιλογές ιδιωτικότητας');
    const text = document.createElement('p');
    text.textContent = english
      ? 'Optional analytics help us understand how the site is used. They load only if you accept.'
      : 'Τα προαιρετικά εργαλεία μέτρησης μας βοηθούν να κατανοούμε τη χρήση του site. Φορτώνουν μόνο αν τα αποδεχτείς.';
    const policy = document.createElement('a');
    policy.href = english ? '/en/aporrito/' : '/aporrito/';
    policy.textContent = english ? 'Privacy policy' : 'Πολιτική απορρήτου';
    const actions = document.createElement('div');
    for (const [value, label] of [
      ['rejected', english ? 'Reject optional' : 'Απόρριψη προαιρετικών'],
      ['accepted', english ? 'Accept analytics' : 'Αποδοχή μέτρησης']
    ]) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = label;
      button.addEventListener('click', () => choose(value));
      actions.appendChild(button);
    }
    text.appendChild(document.createTextNode(' '));
    text.appendChild(policy);
    banner.append(text, actions);
    document.body.appendChild(banner);
  }

  // Consent is shared across studio and legacy pages, including open tabs.
  // Revocation elsewhere must stop this tab's already-loaded integrations too.
  window.addEventListener('storage', event => {
    if (event.key !== 'cookieConsent' && event.key !== null) return;
    try { consent = localStorage.getItem('cookieConsent'); } catch { consent = null; }
    if (consent === 'accepted') {
      document.querySelector('.studio-consent')?.remove();
      enableMeasurement();
    } else if (started) {
      location.reload();
    } else if (consent === 'rejected') {
      document.querySelector('.studio-consent')?.remove();
    } else {
      showChoices();
    }
  });

  // Contact information is never included in event properties or session text.
  document.querySelectorAll('form').forEach(form => form.setAttribute('data-clarity-mask', 'true'));
  document.querySelectorAll('[data-privacy-settings]').forEach(button => {
    button.addEventListener('click', showChoices);
  });
  window.addEventListener('studio:lead-accepted', () => {
    if (consent === 'accepted' && window.gtag) {
      window.gtag('event', 'generate_lead', { event_category: 'engagement', event_label: 'contact_form' });
    }
  });
  document.addEventListener('click', event => {
    const link = event.target.closest('a[href^="tel:"]');
    if (link && consent === 'accepted' && window.gtag) {
      window.gtag('event', 'contact', { event_category: 'engagement', event_label: 'phone_call' });
    }
  });
  if (consent === 'accepted') enableMeasurement();
  else if (consent !== 'rejected') showChoices();
})();