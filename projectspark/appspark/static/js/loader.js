/*
 * SparkyEvents loading indicators (one file, no dependencies).
 *
 *  - Submitting a form  -> full-screen overlay with a spinner and a message.
 *                          Also blocks accidental double-submits.
 *  - Clicking a link    -> slim progress bar across the top of the page right away,
 *                          plus a "Loading <tab name>..." veil.
 *
 * Opt out on any form/link with the attribute  data-no-loader
 * Custom overlay text on a form with           data-loading-text="Doing it..."
 */
(function () {
  'use strict';
  if (window.__sparkyLoader) { return; }
  window.__sparkyLoader = true;

  var BRAND = '#f82249';
  var SLOW_AFTER_MS = 6000;       // show the "server is waking up" hint
  var GIVE_UP_AFTER_MS = 90000;   // never leave the page stuck behind an overlay
  var NAV_LABEL_SCOPE = '.sidebar, .sidebar-nav, .dropdown-menu, .header-nav, .nav-tabs, .nav-pills';

  // First URL segment -> message. Checked as "segment contains key", in order.
  var MESSAGES = [
    ['resend', 'Sending you a new code\u2026'],
    ['verify', 'Verifying your code\u2026'],
    ['register', 'Creating your account and sending your code\u2026'],
    ['login', 'Signing you in\u2026'],
    ['forget', 'Sending your reset link\u2026'],
    ['reset', 'Updating your password\u2026'],
    ['changepassword', 'Updating your password\u2026'],
    ['postevent', 'Posting your event\u2026'],
    ['updateevent', 'Saving your changes\u2026'],
    ['deleteevent', 'Deleting the event\u2026'],
    ['applyforevent', 'Sending your application\u2026'],
    ['approveapp', 'Approving the application\u2026'],
    ['rejectapp', 'Rejecting the application\u2026'],
    ['markeventcompleted', 'Marking the event as completed\u2026'],
    ['profile', 'Saving your profile\u2026'],
    ['feedback', 'Submitting your feedback\u2026'],
    ['logout', 'Signing you out\u2026']
  ];
  var DEFAULT_MESSAGE = 'Please wait\u2026';
  var SLOW_HINT = 'Still working \u2014 the server may be waking up. Thanks for your patience!';

  var overlay, textEl, subEl, bar;
  var slowTimer = null, giveUpTimer = null, barTimer = null;
  var activeForm = null;

  function injectStyles() {
    if (document.querySelector('style[data-sparky-loader]')) { return; }
    var css =
      '#sparky-loader{position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:2147483646;' +
      'display:flex;align-items:center;justify-content:center;background:rgba(15,15,25,.65);' +
      '-webkit-backdrop-filter:blur(3px);backdrop-filter:blur(3px);pointer-events:all}' +
      '#sparky-loader[hidden]{display:none !important;pointer-events:none}' +
      '#sparky-loader.sl-nav{background:rgba(15,15,25,.45);-webkit-backdrop-filter:blur(2px);backdrop-filter:blur(2px)}' +
      '#sparky-loader .sl-box{max-width:340px;margin:16px;padding:24px 32px;border-radius:14px;text-align:center;' +
      'background:#1a1a2e;color:#fff;box-shadow:0 10px 40px rgba(0,0,0,.5);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}' +
      '#sparky-loader .sl-spinner{width:42px;height:42px;margin:0 auto 14px;border-radius:50%;' +
      'border:4px solid rgba(255,255,255,.18);border-top-color:' + BRAND + ';animation:sl-spin .75s linear infinite}' +
      '#sparky-loader .sl-text{margin:0;font-size:16px;font-weight:600;letter-spacing:0.2px}' +
      '#sparky-loader .sl-sub{margin:10px 0 0;font-size:13px;line-height:1.4;color:rgba(255,255,255,.75)}' +
      '#sparky-loader .sl-sub:empty{display:none}' +
      '@keyframes sl-spin{to{transform:rotate(360deg)}}' +
      '#sparky-topbar{position:fixed;top:0;left:0;height:4px;width:0;z-index:2147483647;background:' + BRAND + ';' +
      'box-shadow:0 0 10px ' + BRAND + ',0 0 5px ' + BRAND + ';opacity:0;pointer-events:none}' +
      '@media (prefers-reduced-motion:reduce){#sparky-loader .sl-spinner{animation-duration:2.4s}}';
    var style = document.createElement('style');
    style.setAttribute('data-sparky-loader', '');
    style.appendChild(document.createTextNode(css));
    (document.head || document.documentElement).appendChild(style);
  }

  function build() {
    if (overlay && bar) { return; }
    if (!document.body) { return; }
    injectStyles();

    if (!overlay) {
      overlay = document.createElement('div');
      overlay.id = 'sparky-loader';
      overlay.setAttribute('role', 'status');
      overlay.setAttribute('aria-live', 'polite');
      overlay.hidden = true;
      overlay.innerHTML =
        '<div class="sl-box"><div class="sl-spinner"></div>' +
        '<p class="sl-text"></p><p class="sl-sub"></p></div>';
      textEl = overlay.querySelector('.sl-text');
      subEl = overlay.querySelector('.sl-sub');
      document.body.appendChild(overlay);
    }

    if (!bar) {
      bar = document.createElement('div');
      bar.id = 'sparky-topbar';
      bar.setAttribute('aria-hidden', 'true');
      document.body.appendChild(bar);
    }
  }

  function messageFor(form) {
    var custom = form.getAttribute('data-loading-text');
    if (custom) { return custom; }
    try {
      var url = new URL(form.getAttribute('action') || window.location.href, window.location.href);
      var segment = url.pathname.split('/')[1] || '';
      segment = segment.toLowerCase();
      for (var i = 0; i < MESSAGES.length; i++) {
        if (segment.indexOf(MESSAGES[i][0]) !== -1) { return MESSAGES[i][1]; }
      }
    } catch (e) { /* fall through to default */ }
    return DEFAULT_MESSAGE;
  }

  function showOverlay(message, light) {
    build();
    if (!overlay) { return; }
    overlay.classList.toggle('sl-nav', !!light);
    if (textEl) { textEl.textContent = message || DEFAULT_MESSAGE; }
    if (subEl) { subEl.textContent = ''; }
    overlay.hidden = false;
    clearTimeout(slowTimer);
    clearTimeout(giveUpTimer);
    slowTimer = setTimeout(function () {
      if (subEl && !overlay.hidden) { subEl.textContent = SLOW_HINT; }
    }, SLOW_AFTER_MS);
    giveUpTimer = setTimeout(reset, GIVE_UP_AFTER_MS);
  }

  function reset() {
    clearTimeout(slowTimer);
    clearTimeout(giveUpTimer);
    clearTimeout(barTimer);
    if (overlay) {
      overlay.hidden = true;
      overlay.classList.remove('sl-nav');
      if (subEl) { subEl.textContent = ''; }
    }
    if (bar) {
      bar.style.transition = 'none';
      bar.style.width = '0';
      bar.style.opacity = '0';
    }
    if (activeForm) {
      activeForm.removeAttribute('data-sparky-submitting');
      var buttons = activeForm.querySelectorAll('[type="submit"]');
      for (var i = 0; i < buttons.length; i++) { buttons[i].disabled = false; }
      activeForm = null;
    }
  }

  function showBar() {
    build();
    if (!bar) { return; }
    clearTimeout(barTimer);
    bar.style.transition = 'none';
    bar.style.width = '0';
    bar.style.opacity = '1';
    // Force a reflow so the transition below starts from 0.
    void bar.offsetWidth;
    bar.style.transition = 'width 10s cubic-bezier(.1,.6,.2,1)';
    bar.style.width = '90%';
    barTimer = setTimeout(reset, GIVE_UP_AFTER_MS);
  }

  function onSubmit(e) {
    if (e.defaultPrevented) { return; }
    var form = e.target;
    if (!form || form.tagName !== 'FORM') { return; }
    if (form.hasAttribute('data-no-loader') || (form.target && form.target !== '_self')) { return; }

    if (form.hasAttribute('data-sparky-submitting')) {
      e.preventDefault();
      return;
    }
    form.setAttribute('data-sparky-submitting', '');
    activeForm = form;
    showOverlay(messageFor(form), false);

    // Disable buttons after the browser has collected the form data.
    setTimeout(function () {
      var buttons = form.querySelectorAll('[type="submit"]');
      for (var i = 0; i < buttons.length; i++) { buttons[i].disabled = true; }
    }, 0);
  }

  function isPlainInternalLink(a, e) {
    if (e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) { return false; }
    if (a.hasAttribute('data-no-loader') || a.hasAttribute('download')) { return false; }
    if (a.target && a.target !== '_self') { return false; }
    // Skip interactive Bootstrap widgets (dropdowns, modals, offcanvas, collapse buttons)
    if (a.hasAttribute('data-bs-toggle') || a.hasAttribute('data-bs-target') ||
        a.hasAttribute('data-toggle') || a.hasAttribute('data-target') ||
        a.classList.contains('toggle-sidebar-btn')) {
      return false;
    }
    var href = a.getAttribute('href');
    if (!href || href.charAt(0) === '#' || /^(javascript|mailto|tel):/i.test(href)) { return false; }
    var url;
    try { url = new URL(a.href, window.location.href); } catch (err) { return false; }
    if (url.origin !== window.location.origin) { return false; }
    // Same page with only hash change
    if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) {
      return false;
    }
    return true;
  }

  // "Search Events", "Profile", ... for sidebar / menu links; empty for ordinary links.
  function labelFor(a) {
    var custom = a.getAttribute('data-loading-label');
    if (custom) { return custom; }
    var scoped = a.closest(NAV_LABEL_SCOPE);
    if (scoped) {
      var text = (a.textContent || '').replace(/\s+/g, ' ').trim();
      if (text && text.length <= 40) { return text; }
    }
    return '';
  }

  function onClick(e) {
    if (e.defaultPrevented) { return; }
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a || !isPlainInternalLink(a, e)) { return; }

    var segment = (new URL(a.href, window.location.href).pathname.split('/')[1] || '').toLowerCase();
    if (segment.indexOf('logout') !== -1) {
      showOverlay('Signing you out\u2026', false);
      return;
    }

    var label = labelFor(a);
    showBar();
    showOverlay(label ? 'Loading ' + label + '\u2026' : 'Loading\u2026', true);
  }

  // Setup DOM as early as possible
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', build);
  } else {
    build();
  }

  document.addEventListener('submit', onSubmit, false);
  document.addEventListener('click', onClick, false);

  // Back/forward cache: coming "back" to this page must not show a stale overlay.
  window.addEventListener('pageshow', function (e) { reset(); });

  // Optional manual hooks for custom code: SparkyLoader.show('Text'), SparkyLoader.hide()
  window.SparkyLoader = { show: showOverlay, hide: reset };
})();
