// distilling-videos publication behavior. Loaded before the bundled Alpine.js; GSAP is optional.
// No network access: this file never fetches or posts. It reads the bundled search index from a
// global set by search-index.js and stores only the theme and navigation state in localStorage.
(() => {
  const root = document.documentElement;
  root.classList.replace("no-js", "js");
  const printing = new URLSearchParams(window.location.search).has("print");
  if (printing) root.classList.add("print-mode");

  const store = {
    get(key) {
      try { return window.localStorage.getItem(key); } catch (error) { return null; }
    },
    set(key, value) {
      try {
        if (value === null || value === "") window.localStorage.removeItem(key);
        else window.localStorage.setItem(key, value);
      } catch (error) { /* storage blocked: the choice lasts for this page only */ }
    },
  };
  const media = (query) => window.matchMedia && window.matchMedia(query).matches;
  const narrow = () => media("(max-width: 52rem)");
  const reduced = () => media("(prefers-reduced-motion: reduce)");
  const motion = () => !!window.gsap && !reduced() && !printing && !root.classList.contains("printing");
  const animate = (element, from) => {
    if (!element || !motion()) return;
    try {
      window.gsap.fromTo(element, from, { opacity: 1, x: 0, y: 0, scale: 1, duration: 0.22, ease: "power2.out",
        clearProps: "opacity,transform" });
    } catch (error) { /* motion is decoration; never block the control */ }
  };
  const fold = (text) => (text || "").normalize("NFKD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

  // Print and PDF: open every expanded explanation, finish every tween, show everything.
  const finishMotion = () => {
    if (!window.gsap) return;
    try {
      window.gsap.globalTimeline.getChildren(true, true, false).forEach((tween) => tween.progress(1).kill());
    } catch (error) { /* ignore */ }
  };
  const openAll = () => {
    root.classList.add("printing");
    finishMotion();
    document.querySelectorAll("details:not([open]):not(.md-source)").forEach((details) => {
      details.dataset.printOpened = "true";
      details.open = true;
    });
  };
  const restore = () => {
    root.classList.remove("printing");
    document.querySelectorAll("details[data-print-opened]").forEach((details) => {
      details.open = false;
      delete details.dataset.printOpened;
    });
  };
  if (printing) document.addEventListener("DOMContentLoaded", openAll);
  window.addEventListener("beforeprint", openAll);
  window.addEventListener("afterprint", () => { if (!printing) restore(); });

  // Once-only, subtle section reveals. Content is never hidden in advance: an element is animated
  // from mostly transparent only as it enters the viewport, so no-JS, missing GSAP, reduced motion,
  // print, hash and search targets, and find-in-page all see visible content.
  const reveals = () => {
    if (!motion() || !("IntersectionObserver" in window)) return;
    const observed = new Set();
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        observer.unobserve(entry.target);
        observed.delete(entry.target);
        if (!motion()) return;
        try {
          window.gsap.fromTo(entry.target, { opacity: 0.2, y: 12 },
            { opacity: 1, y: 0, duration: 0.45, ease: "power2.out", clearProps: "opacity,transform" });
        } catch (error) { /* ignore */ }
      });
    }, { rootMargin: "0px 0px -6% 0px" });
    const target = () => {
      const id = decodeURIComponent(window.location.hash.slice(1));
      return id ? document.getElementById(id) : null;
    };
    const skipTarget = (element) => {
      if (!element) return;
      observed.forEach((candidate) => {
        if (candidate.contains(element)) {
          observer.unobserve(candidate);
          observed.delete(candidate);
          if (window.gsap) window.gsap.set(candidate, { clearProps: "opacity,transform" });
        }
      });
    };
    const initial = target();
    document.querySelectorAll(".reveal").forEach((element) => {
      if (element.getBoundingClientRect().top < window.innerHeight) return; // visible at load: never animate
      if (initial && element.contains(initial)) return;
      observed.add(element);
      observer.observe(element);
    });
    // In-page links: the destination must arrive visible, not mid-reveal.
    document.addEventListener("click", (event) => {
      const link = event.target.closest && event.target.closest('a[href*="#"]');
      if (!link) return;
      const url = new URL(link.href, window.location.href);
      if (url.pathname !== window.location.pathname) return;
      skipTarget(document.getElementById(decodeURIComponent(url.hash.slice(1))));
    }, true);
    window.addEventListener("hashchange", () => skipTarget(target()));
  };

  document.addEventListener("alpine:init", () => {
    const Alpine = window.Alpine;

    // Page shell: navigation, theme, search, and the citation evidence panel.
    Alpine.data("shell", () => ({
      mobile: narrow(),
      navOpen: false,
      collapsed: store.get("distill.nav") === "collapsed",
      evidenceTrigger: null,
      navTrigger: null,
      get navVisible() { return this.mobile ? this.navOpen : !this.collapsed; },
      init() {
        const query = window.matchMedia("(max-width: 52rem)");
        const changed = () => {
          this.mobile = query.matches;
          if (!this.mobile) this.setOverlay(false);
          this.sync();
        };
        if (query.addEventListener) query.addEventListener("change", changed);
        this.sync();
        this.initTheme();
        document.addEventListener("click", (event) => this.citation(event));
        reveals();
      },
      sync() {
        root.classList.toggle("nav-collapsed", !this.mobile && this.collapsed);
        root.classList.toggle("nav-open", this.mobile && this.navOpen);
      },
      setOverlay(open) {
        this.navOpen = open;
        const page = document.getElementById("page");
        if (page) page.inert = open;
        this.sync();
      },
      toggleNav() { if (this.navVisible) this.closeNav(); else this.openNav(); },
      openNav() {
        const nav = document.getElementById("site-nav");
        this.navTrigger = document.activeElement;
        if (this.mobile) {
          this.setOverlay(true);
          animate(nav, { opacity: 0, x: -24 });
          this.$nextTick(() => nav.querySelector("a, button").focus());
        } else {
          this.collapsed = false;
          store.set("distill.nav", null);
          this.sync();
          animate(nav, { opacity: 0, x: -12 });
          this.$nextTick(() => nav.querySelector(".nav-close").focus());
        }
      },
      closeNav() {
        if (this.mobile) {
          if (!this.navOpen) return;
          this.setOverlay(false);
        } else {
          this.collapsed = true;
          store.set("distill.nav", "collapsed");
          this.sync();
        }
        this.$nextTick(() => document.querySelector(".menu-button").focus());
      },
      initTheme() {
        const select = document.getElementById("theme-select");
        const saved = root.getAttribute("data-theme") || "";
        const known = select && [...select.options].some((option) => option.value === saved);
        if (saved && !known) {
          root.removeAttribute("data-theme");
          store.set("distill.theme", null);
        }
        if (select) select.value = known ? saved : "";
      },
      setTheme(value) {
        if (value) root.setAttribute("data-theme", value);
        else root.removeAttribute("data-theme");
        store.set("distill.theme", value || null);
      },
      openSearch() {
        const dialog = document.getElementById("search-dialog");
        if (!dialog || dialog.open) return;
        if (this.mobile && this.navOpen) this.setOverlay(false);
        dialog.showModal();
        animate(dialog, { opacity: 0, y: -8 });
        document.getElementById("search-input").focus();
      },
      onKey(event) {
        const typing = event.target.closest && event.target.closest("input, textarea, select, [contenteditable]");
        if ((event.key === "/" && !typing) || (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey))) {
          if (document.querySelector("dialog[open]")) return;
          event.preventDefault();
          this.openSearch();
          return;
        }
        if (event.key === "Escape") {
          if (this.mobile && this.navOpen) { event.preventDefault(); this.closeNav(); return; }
          const panel = document.getElementById("evidence-panel");
          if (panel && !panel.hidden && !document.querySelector("dialog[open]")) { event.preventDefault(); this.closeEvidence(); }
          return;
        }
        if (event.key === "Tab" && this.mobile && this.navOpen) {
          const items = [...document.querySelectorAll("#site-nav a, #site-nav button, #site-nav select")]
            .filter((element) => element.offsetParent !== null);
          const first = items[0];
          const last = items[items.length - 1];
          if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
          else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
        }
      },
      citation(event) {
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        const link = event.target.closest && event.target.closest('sup.cite a[href^="#ref-"], .pull footer a[href^="#ref-"]');
        if (link) {
          const template = document.getElementById("ev-" + link.getAttribute("href").slice(5));
          if (!template) return; // ordinary link to the references list
          event.preventDefault();
          this.openEvidence(template, link);
          return;
        }
        if (event.target.closest && event.target.closest(".evidence-panel .ev-ref")) this.closeEvidence(false);
      },
      openEvidence(template, trigger) {
        const panel = document.getElementById("evidence-panel");
        const body = document.getElementById("evidence-body");
        const wasOpen = !panel.hidden;
        body.replaceChildren(template.content.cloneNode(true));
        this.evidenceTrigger = trigger;
        panel.hidden = false;
        if (!wasOpen) animate(panel, this.mobile ? { opacity: 0, y: 32 } : { opacity: 0, x: 32 });
        document.getElementById("evidence-title").focus({ preventScroll: true });
      },
      closeEvidence(restoreFocus = true) {
        const panel = document.getElementById("evidence-panel");
        if (!panel || panel.hidden) return;
        panel.hidden = true;
        if (restoreFocus && this.evidenceTrigger) this.evidenceTrigger.focus({ preventScroll: true });
        this.evidenceTrigger = null;
      },
    }));

    // Copy Page: the full Markdown twin of this page, whatever is filtered, collapsed, or open.
    Alpine.data("copyPage", () => ({
      label: "Copy page",
      status: "",
      timer: null,
      async copy() {
        const area = document.getElementById("page-markdown");
        const button = this.$root.querySelector(".copy-page");
        const text = area.value;
        let copied = false;
        try {
          if (navigator.clipboard && navigator.clipboard.writeText) {
            await navigator.clipboard.writeText(text);
            copied = true;
          }
        } catch (error) { copied = false; }
        if (!copied) copied = this.legacy(area);
        clearTimeout(this.timer);
        if (copied) {
          this.label = "Copied";
          this.status = `Copied this page's Markdown (${text.length.toLocaleString("en")} characters).`;
          animate(document.getElementById("copy-status"), { opacity: 0, y: 4 });
          this.timer = setTimeout(() => { this.label = "Copy page"; this.status = ""; }, 2500);
        } else {
          const details = area.closest("details");
          details.open = true;
          this.label = "Copy page";
          area.focus({ preventScroll: true });
          area.select();
          area.scrollIntoView({ block: "center" });
          this.status = "Copying was blocked by this browser. The page Markdown is selected below: press Cmd+C or Ctrl+C, or use Download Markdown.";
        }
        if (copied && button && document.activeElement !== button) button.focus({ preventScroll: true });
      },
      legacy(area) {
        const details = area.closest("details");
        const wasOpen = details.open;
        const active = document.activeElement;
        const scroll = [window.scrollX, window.scrollY];
        let copied = false;
        try {
          details.open = true;
          area.focus({ preventScroll: true });
          area.select();
          copied = document.execCommand && document.execCommand("copy") === true;
        } catch (error) { copied = false; }
        if (copied) {
          details.open = wasOpen;
          window.getSelection && window.getSelection().removeAllRanges();
          if (active && active.focus) active.focus({ preventScroll: true });
          window.scrollTo(scroll[0], scroll[1]);
        }
        return copied;
      },
    }));

    // Local filters: hide non-matching items with the hidden attribute (print shows them again).
    Alpine.data("filter", (target) => ({
      q: "",
      summary: "",
      init() { this.$nextTick(() => this.apply()); },
      apply() {
        const list = document.getElementById(target);
        if (!list) return;
        const terms = fold(this.q).split(/\s+/).filter(Boolean);
        const facets = [...this.$root.querySelectorAll("select[data-facet]")]
          .map((select) => [select.dataset.facet, select.value]).filter(([, value]) => value);
        const items = [...list.querySelectorAll("[data-filter-item]")];
        let shown = 0;
        items.forEach((item) => {
          if (item.dataset.text === undefined) item.dataset.text = fold(item.textContent);
          const match = terms.every((term) => item.dataset.text.includes(term)) &&
            facets.every(([facet, value]) => item.dataset[facet] === value);
          item.hidden = !match;
          if (match) shown += 1;
        });
        this.summary = terms.length || facets.length ? `${shown} of ${items.length} shown` : `${items.length} items`;
      },
    }));

    // Offline search over the bundled index. Results are ordinary links built with textContent only.
    Alpine.data("search", () => ({
      q: "",
      summary: "",
      cache: null,
      entries() {
        if (!this.cache) {
          const data = window.DISTILL_SEARCH;
          this.cache = data && Array.isArray(data.entries)
            ? data.entries.map(([href, where, title, text]) => ({ href, where, title, text, hay: fold(title + " " + text), head: fold(title) }))
            : [];
        }
        return this.cache;
      },
      run() {
        const list = this.$refs.results;
        list.replaceChildren();
        const terms = fold(this.q).split(/\s+/).filter(Boolean);
        if (!terms.length) { this.summary = ""; return; }
        const all = this.entries();
        if (!all.length) { this.summary = "The search index did not load. Use the navigation instead."; return; }
        const hits = [];
        all.forEach((entry) => {
          if (!terms.every((term) => entry.hay.includes(term))) return;
          const score = terms.reduce((sum, term) => sum + (entry.head.includes(term) ? 3 : 1), 0);
          hits.push([score, entry]);
        });
        hits.sort((a, b) => b[0] - a[0]);
        hits.slice(0, 60).forEach(([, entry]) => {
          const item = document.createElement("li");
          const link = document.createElement("a");
          link.href = entry.href;
          const where = document.createElement("span");
          where.className = "slug";
          where.textContent = entry.where;
          const title = document.createElement("strong");
          title.textContent = entry.title;
          const snippet = document.createElement("span");
          snippet.className = "snippet";
          this.highlight(snippet, entry.text, terms);
          link.append(where, title, snippet);
          item.append(link);
          list.append(item);
        });
        const total = hits.length;
        this.summary = total ? `${total} result${total === 1 ? "" : "s"}${total > 60 ? " (first 60 shown)" : ""}` : "No results.";
      },
      highlight(node, text, terms) {
        const folded = fold(text);
        let at = -1;
        terms.forEach((term) => { const i = folded.indexOf(term); if (i >= 0 && (at < 0 || i < at)) at = i; });
        const start = Math.max(0, at - 50);
        const piece = text.slice(start, start + 160);
        const foldedPiece = fold(piece);
        // Folding can change length for some scripts; fall back to unhighlighted text then.
        if (foldedPiece.length !== piece.length) { node.textContent = (start ? "…" : "") + piece; return; }
        const marks = [];
        terms.forEach((term) => {
          let i = foldedPiece.indexOf(term);
          while (i >= 0) { marks.push([i, i + term.length]); i = foldedPiece.indexOf(term, i + term.length); }
        });
        marks.sort((a, b) => a[0] - b[0]);
        let cursor = 0;
        if (start) node.append("…");
        marks.forEach(([from, to]) => {
          if (from < cursor) return;
          node.append(piece.slice(cursor, from));
          const mark = document.createElement("mark");
          mark.textContent = piece.slice(from, to);
          node.append(mark);
          cursor = to;
        });
        node.append(piece.slice(cursor));
      },
      first() { const link = this.$refs.results.querySelector("a"); if (link) link.focus(); },
      picked(event) {
        const link = event.target.closest("a");
        if (!link) return;
        const url = new URL(link.href, window.location.href);
        if (url.pathname === window.location.pathname) this.close();
      },
      close() { document.getElementById("search-dialog").close(); },
    }));

    // Gallery viewer: zoom, pan, fit, previous and next by buttons, keyboard, pointer, and touch.
    Alpine.data("gallery", () => ({
      index: 0,
      count: 0,
      scale: 1,
      x: 0,
      y: 0,
      links: [],
      pointers: new Map(),
      gesture: null,
      trigger: null,
      open(event) {
        const link = event.target.closest(".g-open");
        if (!link || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
        event.preventDefault();
        this.links = [...document.querySelectorAll(".g-item:not([hidden]) .g-open")];
        this.count = this.links.length;
        this.trigger = link;
        this.$refs.viewer.showModal();
        this.show(Math.max(0, this.links.indexOf(link)));
        this.$refs.viewer.querySelector(".viewer-close").focus();
      },
      show(index) {
        if (!this.count) return;
        this.index = (index + this.count) % this.count;
        const link = this.links[this.index];
        const image = this.$refs.image;
        image.src = link.getAttribute("href");
        image.alt = link.querySelector("img").alt;
        const caption = link.closest("figure").querySelector("figcaption");
        this.$refs.caption.replaceChildren(...[...caption.childNodes].map((node) => node.cloneNode(true)));
        this.fit();
        animate(image, { opacity: 0, scale: 0.98 });
      },
      prev() { this.show(this.index - 1); },
      next() { this.show(this.index + 1); },
      apply() {
        this.$refs.image.style.transform = `translate(${this.x}px, ${this.y}px) scale(${this.scale})`;
        this.$refs.stage.classList.toggle("zoomed", this.scale > 1);
      },
      fit() { this.scale = 1; this.x = 0; this.y = 0; this.apply(); },
      zoom(factor) {
        this.scale = Math.min(8, Math.max(1, this.scale * factor));
        if (this.scale === 1) { this.x = 0; this.y = 0; }
        this.apply();
      },
      toggleZoom() { if (this.scale > 1) this.fit(); else this.zoom(2); },
      pan(dx, dy) { if (this.scale > 1) { this.x += dx; this.y += dy; this.apply(); } },
      key(event) {
        if (event.target.closest("button") && (event.key === "Enter" || event.key === " ")) return;
        const step = 48;
        const zoomed = this.scale > 1;
        const actions = {
          ArrowLeft: () => (zoomed ? this.pan(step, 0) : this.prev()),
          ArrowRight: () => (zoomed ? this.pan(-step, 0) : this.next()),
          ArrowUp: () => this.pan(0, step),
          ArrowDown: () => this.pan(0, -step),
          "+": () => this.zoom(1.5),
          "=": () => this.zoom(1.5),
          "-": () => this.zoom(1 / 1.5),
          0: () => this.fit(),
          Home: () => this.show(0),
          End: () => this.show(this.count - 1),
        };
        if (actions[event.key]) { event.preventDefault(); actions[event.key](); }
      },
      down(event) {
        this.$refs.stage.setPointerCapture && this.$refs.stage.setPointerCapture(event.pointerId);
        this.pointers.set(event.pointerId, [event.clientX, event.clientY]);
        if (this.pointers.size === 2) {
          const [a, b] = [...this.pointers.values()];
          this.gesture = { pinch: Math.hypot(a[0] - b[0], a[1] - b[1]), scale: this.scale };
        } else {
          this.gesture = { x: event.clientX, y: event.clientY, startX: this.x, startY: this.y, moved: false };
        }
      },
      move(event) {
        if (!this.pointers.has(event.pointerId) || !this.gesture) return;
        this.pointers.set(event.pointerId, [event.clientX, event.clientY]);
        if (this.gesture.pinch && this.pointers.size === 2) {
          const [a, b] = [...this.pointers.values()];
          this.scale = Math.min(8, Math.max(1, this.gesture.scale * Math.hypot(a[0] - b[0], a[1] - b[1]) / this.gesture.pinch));
          if (this.scale === 1) { this.x = 0; this.y = 0; }
          this.apply();
        } else if (this.scale > 1) {
          this.x = this.gesture.startX + event.clientX - this.gesture.x;
          this.y = this.gesture.startY + event.clientY - this.gesture.y;
          this.apply();
        }
      },
      up(event) {
        const gesture = this.gesture;
        this.pointers.delete(event.pointerId);
        if (gesture && !gesture.pinch && this.scale === 1 && event.type === "pointerup") {
          const dx = event.clientX - gesture.x;
          if (Math.abs(dx) > 50 && Math.abs(dx) > Math.abs(event.clientY - gesture.y)) {
            if (dx < 0) this.next(); else this.prev();
          }
        }
        if (!this.pointers.size) this.gesture = null;
      },
      wheel(event) {
        if (!event.ctrlKey && !event.metaKey) return;
        event.preventDefault();
        this.zoom(event.deltaY < 0 ? 1.15 : 1 / 1.15);
      },
      close() { this.$refs.viewer.close(); },
      closed() {
        this.$refs.image.removeAttribute("src");
        if (this.trigger) this.trigger.focus();
      },
    }));

    // Figure zoom uses the native modal dialog: focus moves in, Escape closes it.
    Alpine.data("zoom", () => ({
      open() { this.$refs.dialog.showModal(); },
      close() { this.$refs.dialog.close(); },
    }));
    // Demo step-through. Without JavaScript, or when printing, every step stays visible.
    Alpine.data("stepper", (n) => ({
      i: 0,
      n,
      prev() { if (this.i > 0) this.i -= 1; },
      next() { if (this.i < this.n - 1) this.i += 1; },
      go(k) { this.i = k; },
    }));
  });
})();
