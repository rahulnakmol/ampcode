// Applies the reader's saved theme and navigation state before first paint. Storage may be
// unavailable (file:// policies, private modes): every access is guarded and failure keeps the default.
(function () {
  var root = document.documentElement;
  try {
    var theme = window.localStorage.getItem("distill.theme");
    if (theme && /^[a-z0-9-]{1,40}$/.test(theme)) root.setAttribute("data-theme", theme);
    if (window.localStorage.getItem("distill.nav") === "collapsed") root.classList.add("nav-collapsed");
  } catch (error) {
    /* storage blocked: keep the system default theme and an expanded navigation */
  }
  // The saved collapse is only honored once the page shell (Alpine) has initialized and marked the page
  // ready, because only the shell can show the navigation again. If Alpine or article.js failed to load or
  // run, the navigation comes back by the load event and the JavaScript-only controls stay hidden.
  window.addEventListener("load", function () {
    if (!root.classList.contains("ready")) root.classList.remove("nav-collapsed", "nav-open");
  });
})();
