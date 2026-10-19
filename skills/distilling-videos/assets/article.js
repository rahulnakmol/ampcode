// distilling-videos article behavior. Loaded before the bundled Alpine.js.
// No network access: this file never fetches, posts, or reads storage.
(() => {
  const root = document.documentElement;
  root.classList.replace("no-js", "js");
  const printing = new URLSearchParams(window.location.search).has("print");

  // Static equivalents for print and PDF: open every expanded explanation.
  const openAll = () => {
    document.querySelectorAll("details:not([open])").forEach((details) => {
      details.dataset.printOpened = "true";
      details.open = true;
    });
  };
  const restore = () => {
    document.querySelectorAll("details[data-print-opened]").forEach((details) => {
      details.open = false;
      delete details.dataset.printOpened;
    });
  };
  if (printing) {
    root.classList.add("print-mode");
    document.addEventListener("DOMContentLoaded", openAll);
  }
  window.addEventListener("beforeprint", openAll);
  window.addEventListener("afterprint", () => {
    if (!printing) restore();
  });

  document.addEventListener("alpine:init", () => {
    // Figure zoom uses the native modal dialog: focus moves in, Escape closes it.
    window.Alpine.data("zoom", () => ({
      open() {
        this.$refs.dialog.showModal();
      },
      close() {
        this.$refs.dialog.close();
      },
    }));
    // Demo step-through. Without JavaScript, or when printing, every step stays visible.
    window.Alpine.data("stepper", (n) => ({
      i: 0,
      n,
      prev() {
        if (this.i > 0) this.i -= 1;
      },
      next() {
        if (this.i < this.n - 1) this.i += 1;
      },
      go(k) {
        this.i = k;
      },
    }));
  });
})();
