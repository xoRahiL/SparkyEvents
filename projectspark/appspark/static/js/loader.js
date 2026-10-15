/*
 * SparkyEvents loading indicators (one file, no dependencies).
 *
 *  - Submitting a form  -> full-screen overlay with a spinner and a message.
 *                          Also blocks accidental double-submits.
 *  - Clicking a link    -> slim progress bar across the top of the page.
 *
 * Opt out on any form/link with the attribute  data-no-loader
 * Custom overlay text on a form with           data-loading-text="Doing it..."
 */
(function () {
  'use strict';
  if (window.__sparkyLoader) { return; }
  window.__sparkyLoader = true;

  var BRAND = '#f82249';
  var SLOW_AFTER_MS = 8000;      // show the "server is waking up" hint
  var GIVE_UP_AFTER_MS = 90000;  // never leave the page stuck behind an overlay

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
    var css =
      '#sparky-loader{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;' +
      'justify-content:center;background:rgba(15,15,25,.6);-webkit-backdrop-filter:blur(2px);backdrop-filter:blur(2px)}' +
      '#sparky-loader[hidden]{display:none}' +
      '#sparky-loader .sl-box{max-width:320px;margin:16px;padding:28px 32px;border-radius:12px;text-align:center;' +
      'background:#1a1a2e;color:#fff;box-shadow:0 10px 40px rgba(0,0,0,.45);font-family:inherit}' +
      '#sparky-loader .sl-spinner{width:44px;height:44px;margin:0 auto 16px;border-radius:50%;' +
      'border:4px solid rgba(255,255,255,.2);border-top-color:' + BRAND + ';animation:sl-spin .8s linear infinite}' +
      '#sparky-loader .sl-text{margin:0;font-size:16px;font-weight:600}' +
      '#sparky-loader .sl-sub{margin:10px 0 0;font-size:13px;line-height:1.4;color:rgba(255,255,255,.7)}' +
      '#sparky-loader .sl-sub:empty{display:none}' +
      '@keyframes sl-spin{to{transform:rotate(360deg)}}' +
      '#sparky-topbar{position:fixed;top:0;left:0;height:3px;width:0;z-index:2147483001;background:' + BRAND + ';' +
      'box-shadow:0 0 8px ' + BRAND + ';opacity:0;pointer-events:none}' +
      '@media (prefers-reduced-motion:reduce){#sparky-loader .sl-spinner{animation-duration:2.4s}}';
    var style = document.createElement('style');
    style.setAttribute('data-sparky-loader', '');
    style.appendChild(document.createTextNode(css));
    document.head.appendChild(style);
  }

  function build() {
    if (overlay) { return; }
    injectStyles();

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

    bar = document.createElement('div');
    bar.id = 'sparky-topbar';
    bar.setAttribute('aria-hidden', 'true');

    document.body.appendChild(overlay);
    document.body.appendChild(bar);
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

  function showOverlay(message) {
    build();
    textEl.textContent = message || DEFAULT_MESSAGE;
    subEl.textContent = '';
    overlay.hidden = false;
    clearTimeout(slowTimer);
    clearTimeout(giveUpTimer);
    slowTimer = setTimeout(function () { subEl.textContent = SLOW_HINT; }, SLOW_AFTER_MS);
    giveUpTimer = setTimeout(reset, GIVE_UP_AFTER_MS);
  }

  function reset() {
    clearTimeout(slowTimer);
    clearTimeout(giveUpTimer);
    clearTimeout(barTimer);
    if (overlay) { overlay.hidden = true; subEl.textContent = ''; }
    if (bar) { bar.style.transition = 'none'; bar.style.width = '0'; bar.style.opacity = '0'; }
    if (activeForm) {
      activeForm.removeAttribute('data-sparky-submitting');
      var buttons = activeForm.querySelectorAll('[type="submit"]');
      for (var i = 0; i < buttons.length; i++) { buttons[i].disabled = false; }
      activeForm = null;
    }
  }

  function showBar() {
    build();
    clearTimeout(barTimer);
    bar.style.transition = 'none';
    bar.style.width = '0';
    bar.style.opacity = '1';
    // Force a reflow so the transition below starts from 0.
    void bar.offsetWidth;
    bar.style.transition = 'width 10s cubic-bezier(.1,.6,.2,1)';
    bar.style.width = '88%';
    barTimer = setTimeout(reset, GIVE_UP_AFTER_MS);
  }

  function onSubmit(e) {
    if (e.defaultPrevented) { return; }                 // e.g. the user cancelled a confirm() dialog
    var form = e.target;
    if (!form || form.tagName !== 'FORM') { return; }
    if (form.hasAttribute('data-no-loader') || (form.target && form.target !== '_self')) { return; }

    if (form.hasAttribute('data-sparky-submitting')) {  // already on its way: ignore the second submit
      e.preventDefault();
      return;
    }
    form.setAttribute('data-sparky-submitting', '');
    activeForm = form;
    showOverlay(messageFor(form));

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
    var href = a.getAttribute('href');
    if (!href || href.charAt(0) === '#' || /^(javascript|mailto|tel):/i.test(href)) { return false; }
    var url;
    try { url = new URL(a.href, window.location.href); } catch (err) { return false; }
    if (url.origin !== window.location.origin) { return false; }
    // Same page, only the #hash differs: nothing will load.
    if (url.pathname === window.location.pathname && url.search === window.location.search && url.hash) { return false; }
    return true;
  }

  function onClick(e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a || !isPlainInternalLink(a, e)) { return; }
    // Wait one tick so other handlers (Bootstrap, confirm dialogs) can cancel the click first.
    setTimeout(function () {
      if (e.defaultPrevented) { return; }
      var segment = (new URL(a.href, window.location.href).pathname.split('/')[1] || '').toLowerCase();
      if (segment.indexOf('logout') !== -1) { showOverlay('Signing you out\u2026'); }
      else { showBar(); }
    }, 0);
  }

  document.addEventListener('submit', onSubmit, false);
  document.addEventListener('click', onClick, false);
  // Back/forward cache: coming "back" to this page must not show a stale overlay.
  window.addEventListener('pageshow', function (e) { if (e.persisted) { reset(); } });

  // Optional manual hooks for custom code: SparkyLoader.show('Text'), SparkyLoader.hide()
  window.SparkyLoader = { show: showOverlay, hide: reset };
})();
