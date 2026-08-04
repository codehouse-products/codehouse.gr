/* Artivo AI — Premium Estiasi Template JS */
(function () {
  'use strict';

  /* Preloader */
  window.addEventListener('load', function () {
    setTimeout(function () {
      var pre = document.getElementById('preloader');
      if (pre) pre.classList.add('done');
    }, 900);
  });

  /* Custom cursor */
  var dot = document.getElementById('cursorDot');
  var ring = document.getElementById('cursorRing');
  if (dot && ring && window.matchMedia('(hover: hover)').matches) {
    var rx = 0, ry = 0, tx = 0, ty = 0;
    document.addEventListener('mousemove', function (e) {
      tx = e.clientX; ty = e.clientY;
      dot.style.left = tx + 'px'; dot.style.top = ty + 'px';
    });
    (function animateRing() {
      rx += (tx - rx) * 0.16; ry += (ty - ry) * 0.16;
      ring.style.left = rx + 'px'; ring.style.top = ry + 'px';
      requestAnimationFrame(animateRing);
    })();
    document.querySelectorAll('a, button, .menu-tab, input, select, textarea, .g-item').forEach(function (el) {
      el.addEventListener('mouseenter', function () { ring.classList.add('is-hover'); });
      el.addEventListener('mouseleave', function () { ring.classList.remove('is-hover'); });
    });
  }

  /* Nav scroll state */
  var nav = document.getElementById('nav');
  window.addEventListener('scroll', function () {
    if (window.scrollY > 60) nav.classList.add('scrolled');
    else nav.classList.remove('scrolled');
  }, { passive: true });

  /* Mobile burger */
  var burger = document.getElementById('navBurger');
  var links = document.getElementById('navLinks');
  if (burger && links) {
    burger.addEventListener('click', function () {
      burger.classList.toggle('open');
      links.classList.toggle('open');
    });
    links.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        burger.classList.remove('open');
        links.classList.remove('open');
      });
    });
  }

  /* Reveal on scroll */
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (en.isIntersecting) { en.target.classList.add('visible'); io.unobserve(en.target); }
    });
  }, { threshold: 0.12 });
  document.querySelectorAll('.reveal').forEach(function (el) { io.observe(el); });

  /* Counters */
  var cio = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      var el = en.target;
      var target = parseInt(el.getAttribute('data-count'), 10) || 0;
      var dur = 1800, start = null;
      function step(ts) {
        if (!start) start = ts;
        var p = Math.min((ts - start) / dur, 1);
        el.textContent = Math.floor(target * (1 - Math.pow(1 - p, 3)));
        if (p < 1) requestAnimationFrame(step);
      }
      requestAnimationFrame(step);
      cio.unobserve(el);
    });
  }, { threshold: 0.4 });
  document.querySelectorAll('.stat-num').forEach(function (el) { cio.observe(el); });

  /* Parallax hero & feature */
  var heroImg = document.querySelector('.hero-bg img');
  var featImg = document.querySelector('.feature-bg img');
  window.addEventListener('scroll', function () {
    var y = window.scrollY;
    if (heroImg && y < window.innerHeight) heroImg.style.transform = 'translateY(' + y * 0.25 + 'px)';
    if (featImg) {
      var r = featImg.closest('.feature-banner').getBoundingClientRect();
      if (r.top < window.innerHeight && r.bottom > 0) {
        featImg.style.transform = 'translateY(' + (r.top * -0.12) + 'px)';
      }
    }
  }, { passive: true });

  /* Menu tabs */
  var tabs = document.querySelectorAll('.menu-tab');
  var panels = document.querySelectorAll('.menu-panel');
  tabs.forEach(function (tab) {
    tab.addEventListener('click', function () {
      tabs.forEach(function (t) { t.classList.remove('active'); });
      panels.forEach(function (p) { p.classList.remove('active'); });
      tab.classList.add('active');
      var panel = document.getElementById('panel-' + tab.getAttribute('data-tab'));
      if (panel) panel.classList.add('active');
    });
  });

  /* Testimonials slider */
  var cards = document.querySelectorAll('.testi-card');
  var dotsWrap = document.getElementById('testiDots');
  if (cards.length && dotsWrap) {
    var idx = 0, timer;
    cards.forEach(function (_, i) {
      var b = document.createElement('button');
      b.className = 'testi-dot' + (i === 0 ? ' active' : '');
      b.setAttribute('aria-label', 'Κριτική ' + (i + 1));
      b.addEventListener('click', function () { go(i); restart(); });
      dotsWrap.appendChild(b);
    });
    var dots = dotsWrap.querySelectorAll('.testi-dot');
    function go(i) {
      cards[idx].classList.remove('active'); dots[idx].classList.remove('active');
      idx = i;
      cards[idx].classList.add('active'); dots[idx].classList.add('active');
    }
    function next() { go((idx + 1) % cards.length); }
    function restart() { clearInterval(timer); timer = setInterval(next, 5200); }
    restart();
  }

  /* Reservation form (demo) */
  var form = document.getElementById('reservationForm');
  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var btn = form.querySelector('button[type="submit"]');
      btn.textContent = 'Η κράτηση εστάλη ✓';
      btn.disabled = true;
      setTimeout(function () {
        btn.textContent = 'Αποστολή Κράτησης';
        btn.disabled = false;
        form.reset();
      }, 3500);
    });
  }

  /* Year */
  var yr = document.getElementById('year');
  if (yr) yr.textContent = new Date().getFullYear();
})();
