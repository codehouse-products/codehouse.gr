/* CODEHOUSE.GR — interactions */
(function () {
  'use strict';

  /* ---------- Start infinite animations after load (Speed Index) ---------- */
  var startAnims = function () {
    setTimeout(function () { document.body.classList.add('anim-on'); }, 2500);
  };
  if (document.readyState === 'complete') { startAnims(); }
  else { window.addEventListener('load', startAnims); }

  /* ---------- Promo banner ---------- */
  var promo = document.getElementById('promoBanner');
  var promoClose = document.getElementById('promoClose');
  if (promo) {
    var promoDismissed = false;
    try { promoDismissed = sessionStorage.getItem('promoClosed') === '1'; } catch (e) {}
    if (promoDismissed) {
      promo.classList.add('hidden');
      promo.style.display = 'none';
    } else {
      document.body.classList.add('has-promo');
    }
    if (promoClose) {
      promoClose.addEventListener('click', function () {
        promo.classList.add('hidden');
        document.body.classList.remove('has-promo');
        try { sessionStorage.setItem('promoClosed', '1'); } catch (e) {}
        setTimeout(function () { promo.style.display = 'none'; }, 500);
      });
    }
  }

  /* ---------- Nav ---------- */
  var nav = document.getElementById('nav');
  var onScroll = function () {
    nav.classList.toggle('scrolled', window.scrollY > 30);
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  var burger = document.getElementById('navBurger');
  var mobileMenu = document.getElementById('mobileMenu');
  var toggleMenu = function (open) {
    var isOpen = typeof open === 'boolean' ? open : !mobileMenu.classList.contains('open');
    mobileMenu.classList.toggle('open', isOpen);
    burger.classList.toggle('open', isOpen);
    burger.setAttribute('aria-expanded', String(isOpen));
    document.body.style.overflow = isOpen ? 'hidden' : '';
  };
  burger.addEventListener('click', function () { toggleMenu(); });
  mobileMenu.querySelectorAll('a').forEach(function (a) {
    a.addEventListener('click', function () { toggleMenu(false); });
  });

  /* ---------- Custom cursor (desktop) ---------- */
  if (window.matchMedia('(pointer: fine)').matches) {
    var dot = document.querySelector('.cursor-dot');
    var ring = document.querySelector('.cursor-ring');
    var rx = 0, ry = 0, tx = 0, ty = 0;
    document.addEventListener('mousemove', function (e) {
      tx = e.clientX; ty = e.clientY;
      dot.style.left = tx + 'px'; dot.style.top = ty + 'px';
    });
    (function ringLoop() {
      rx += (tx - rx) * 0.16; ry += (ty - ry) * 0.16;
      ring.style.left = rx + 'px'; ring.style.top = ry + 'px';
      requestAnimationFrame(ringLoop);
    })();
    document.querySelectorAll('a, button, .opt span, summary').forEach(function (el) {
      el.addEventListener('mouseenter', function () { ring.classList.add('hovering'); });
      el.addEventListener('mouseleave', function () { ring.classList.remove('hovering'); });
    });
  }

  /* ---------- Reveal on scroll ---------- */
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); }
    });
  }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
  document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });

  /* ---------- Counter stats ---------- */
  var statIO = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      statIO.unobserve(en.target);
      var el = en.target, target = parseInt(el.getAttribute('data-count'), 10);
      var start = null, dur = 1400;
      var step = function (ts) {
        if (!start) start = ts;
        var p = Math.min((ts - start) / dur, 1);
        el.textContent = Math.round(target * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
  }, { threshold: 0.5 });
  document.querySelectorAll('.stat strong[data-count]').forEach(function (el) { statIO.observe(el); });

  /* ---------- Service card glow follows cursor ---------- */
  document.querySelectorAll('.service-card').forEach(function (card) {
    card.addEventListener('mousemove', function (e) {
      var r = card.getBoundingClientRect();
      card.style.setProperty('--mx', (e.clientX - r.left) + 'px');
      card.style.setProperty('--my', (e.clientY - r.top) + 'px');
    });
  });

  /* ---------- Code window tilt ---------- */
  var codeWin = document.querySelector('.code-window');
  if (codeWin && window.matchMedia('(pointer: fine)').matches) {
    var hero = document.getElementById('hero');
    hero.addEventListener('mousemove', function (e) {
      var cx = window.innerWidth / 2, cy = window.innerHeight / 2;
      var dx = (e.clientX - cx) / cx, dy = (e.clientY - cy) / cy;
      codeWin.style.transform = 'rotateY(' + (dx * 6) + 'deg) rotateX(' + (-dy * 6) + 'deg)';
    });
    hero.addEventListener('mouseleave', function () { codeWin.style.transform = ''; });
  }

  /* ---------- Typewriter rotate hero accent ---------- */
  var typeEl = document.getElementById('typeword');
  if (typeEl) {
    var words = ['ψηφιακά σπίτια', 'ιστοσελίδες', 'e-shops', 'QR μενού', 'εμπειρίες'];
    var wi = 0;
    setTimeout(function () {
    setInterval(function () {
      wi = (wi + 1) % words.length;
      typeEl.style.transition = 'opacity .35s, transform .35s';
      typeEl.style.opacity = '0';
      typeEl.style.transform = 'translateY(14px)';
      setTimeout(function () {
        typeEl.textContent = words[wi];
        typeEl.style.opacity = '1';
        typeEl.style.transform = 'translateY(0)';
      }, 360);
    }, 3200);
    }, 3000);
  }

  /* ---------- QUIZ ---------- */
  var TOTAL_STEPS = 7;
  var current = 1;
  var form = document.getElementById('quizForm');
  var bar = document.getElementById('quizBar');
  var btnPrev = document.getElementById('quizPrev');
  var btnNext = document.getElementById('quizNext');
  var quizNav = document.getElementById('quizNav');
  var successBox = document.getElementById('quizSuccess');

  function showStep(n) {
    form.querySelectorAll('.quiz-step').forEach(function (s) {
      s.classList.toggle('active', parseInt(s.getAttribute('data-step'), 10) === n);
    });
    bar.style.width = (n / TOTAL_STEPS * 100) + '%';
    btnPrev.disabled = n === 1;
    btnNext.textContent = n === TOTAL_STEPS ? 'Αποστολή ✓' : 'Επόμενο →';
    current = n;
  }

  function validateStep(n) {
    if (n === 7) {
      var name = form.querySelector('input[name="name"]');
      var phone = form.querySelector('input[name="phone"]');
      var ok = true;
      [name, phone].forEach(function (f) {
        var bad = !f.value.trim();
        f.classList.toggle('error', bad);
        if (bad) ok = false;
      });
      return ok;
    }
    return true; // τα βήματα επιλογών είναι προαιρετικά — μην μπλοκάρεις τον χρήστη
  }

  function collectData() {
    var data = {};
    var fd = new FormData(form);
    fd.forEach(function (v, k) {
      if (data[k]) { data[k] += ' | ' + v; } else { data[k] = v; }
    });
    data._timestamp = new Date().toISOString();
    data._page = location.href;
    return data;
  }

  function submitQuiz() {
    var data = collectData();
    // 1) Αποθήκευση τοπικά (backup)
    try {
      var all = JSON.parse(localStorage.getItem('ch_leads') || '[]');
      all.push(data);
      localStorage.setItem('ch_leads', JSON.stringify(all));
    } catch (e) {}

    // 2) Αποστολή στο backend endpoint (αν υπάρχει), αλλιώς mailto fallback
    var payload = JSON.stringify(data);
    fetch('lead.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: payload
    }).then(function() {
      if (typeof gtag === 'function') {
        gtag('event', 'generate_lead', { 'event_category': 'engagement', 'event_label': 'homepage_quiz_success' });
      }
    }).catch(function () { /* silent — το localStorage κρατά backup */ });

    // 3) Εμφάνιση επιτυχίας
    form.querySelectorAll('.quiz-step').forEach(function (s) { s.classList.remove('active'); });
    quizNav.style.display = 'none';
    bar.style.width = '100%';
    successBox.hidden = false;
  }

  btnNext.addEventListener('click', function () {
    if (!validateStep(current)) return;
    if (current === TOTAL_STEPS) { submitQuiz(); return; }
    showStep(current + 1);
  });
  btnPrev.addEventListener('click', function () {
    if (current > 1) showStep(current - 1);
  });

  // Auto-advance στα radio βήματα (μικρή καθυστέρηση για να φανεί η επιλογή)
  form.querySelectorAll('.quiz-step input[type="radio"]').forEach(function (input) {
    input.addEventListener('change', function () {
      var stepEl = input.closest('.quiz-step');
      var stepNum = parseInt(stepEl.getAttribute('data-step'), 10);
      // step 6 έχει 2 ομάδες radios — μην προχωράς αυτόματα
      if (stepNum === 6 || stepNum === TOTAL_STEPS) return;
      setTimeout(function () {
        if (current === stepNum) showStep(stepNum + 1);
      }, 420);
    });
  });

  showStep(1);

  /* ---------- SWIPER SERVICES ---------- */
  var serviceSwiper;
  if (document.querySelector('.service-cards')) {
    serviceSwiper = new Swiper('.service-cards', {
      slidesPerView: 1,
      spaceBetween: 20,
      loop: true,
      grabCursor: true,
      observer: true,
      observeParents: true,
      a11y: {
        enabled: true,
        containerRoleDescriptionMessage: 'carousel',
        slideRole: 'listitem',
        itemRoleDescriptionMessage: 'slide'
      },
      wrapperClass: 'swiper-wrapper',
      navigation: {
        nextEl: '.swiper-button-next',
        prevEl: '.swiper-button-prev',
      },
      pagination: {
        el: '.service-cards .swiper-pagination',
        type: 'progressbar',
      },
      breakpoints: {
        768: { slidesPerView: 2 },
        1024: { slidesPerView: 3 },
        1200: { 
          slidesPerView: 4,
          allowTouchMove: false,
          navigation: false
        }
      }
    });
  }

  /* ---------- Smooth anchor offset for fixed nav ---------- */
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      var id = a.getAttribute('href');
      if (id.length < 2) return;
      var target = document.querySelector(id);
      if (!target) return;
      e.preventDefault();
      var y = target.getBoundingClientRect().top + window.scrollY - 70;
      window.scrollTo({ top: y, behavior: 'smooth' });
    });
  });
})();
