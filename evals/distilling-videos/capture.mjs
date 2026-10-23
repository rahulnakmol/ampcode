#!/usr/bin/env node
// Drives a real Chromium-family browser over the DevTools protocol (no npm dependencies) to check and
// capture rendered distilling-videos publications opened via file:// with a dead proxy (offline).
//
// Usage: node capture.mjs BROWSER OUT_DIR DIST_DIR [DIST_DIR...]
// Writes OUT_DIR/<publication>/*.png and OUT_DIR/report.json ({publication: {checks, details}}).
// Any request that is not file: or data: is recorded as a remote request (the pages must make none).
import { spawn } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [browser, outDir, ...dists] = process.argv.slice(2);
if (!browser || !outDir || !dists.length) {
  console.error("usage: node capture.mjs BROWSER OUT_DIR DIST_DIR [DIST_DIR...]");
  process.exit(2);
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function launch() {
  const profile = mkdtempSync(join(tmpdir(), "distill-capture-"));
  const proc = spawn(browser, [
    "--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "--no-first-run",
    "--no-default-browser-check", "--disable-extensions", "--proxy-server=127.0.0.1:9", "--hide-scrollbars",
    "about:blank",
  ], { stdio: "ignore" });
  const portFile = join(profile, "DevToolsActivePort");
  for (let i = 0; i < 100 && !existsSync(portFile); i++) await sleep(100);
  const port = readFileSync(portFile, "utf8").split("\n")[0];
  const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = targets.find((t) => t.type === "page");
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((r, j) => { ws.onopen = r; ws.onerror = j; });
  let id = 0;
  const pending = new Map();
  const listeners = [];
  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const { resolve: ok, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : ok(msg.result);
    } else if (msg.method) {
      listeners.forEach((fn) => fn(msg));
    }
  };
  const send = (method, params = {}) => new Promise((ok, reject) => {
    const n = ++id;
    pending.set(n, { resolve: ok, reject });
    ws.send(JSON.stringify({ id: n, method, params }));
  });
  const close = () => { ws.close(); proc.kill("SIGTERM"); setTimeout(() => rmSync(profile, { recursive: true, force: true }), 500); };
  return { send, on: (fn) => listeners.push(fn), close };
}

async function main() {
  const cdp = await launch();
  const { send } = cdp;
  const log = { remote: [], console: [], exceptions: [] };
  let loaded = null;
  cdp.on((msg) => {
    if (msg.method === "Network.requestWillBeSent") {
      const url = msg.params.request.url;
      if (!/^(file|data|about|blob):/.test(url)) log.remote.push(url);
    } else if (msg.method === "Runtime.consoleAPICalled" && ["error", "warning", "assert"].includes(msg.params.type)) {
      log.console.push(msg.params.args.map((a) => a.value ?? a.description).join(" "));
    } else if (msg.method === "Runtime.exceptionThrown") {
      log.exceptions.push(msg.params.exceptionDetails.exception?.description ?? msg.params.exceptionDetails.text);
    } else if (msg.method === "Page.loadEventFired" && loaded) {
      loaded();
    }
  });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Network.enable");
  try {
    await send("Browser.grantPermissions", { permissions: ["clipboardReadWrite", "clipboardSanitizedWrite"] });
  } catch (error) { /* older browsers: the clipboard checks below record what happened */ }

  const evaluate = async (expression) => {
    const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true, userGesture: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + " " + (r.exceptionDetails.exception?.description ?? "") + " :: " + expression.slice(0, 120));
    return r.result.value;
  };
  const navigate = async (url, settle = 700) => {
    const done = new Promise((r) => { loaded = r; });
    await send("Page.navigate", { url });
    await Promise.race([done, sleep(10000)]);
    loaded = null;
    await sleep(settle);
  };
  const viewport = (width, height, mobile = false, scale = 1) =>
    send("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: scale, mobile });
  const loadLazy = async () => {
    await evaluate(`(async () => { document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager');
      await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(r => { i.onload = i.onerror = r; })));
      window.scrollTo(0, 0); })()`);
    await sleep(300);
  };
  const shot = async (file, clip) => {
    const params = { format: "png", captureBeyondViewport: !!clip };
    if (clip) params.clip = { ...clip, scale: 1 };
    const { data } = await send("Page.captureScreenshot", params);
    writeFileSync(file, Buffer.from(data, "base64"));
  };
  const fullShot = async (file) => {
    const m = await send("Page.getLayoutMetrics");
    const size = m.cssContentSize || m.contentSize;
    await shot(file, { x: 0, y: 0, width: Math.ceil(size.width), height: Math.min(Math.ceil(size.height), 16000) });
  };
  const elementShot = async (file, selector, pad = 16, fullWidth = false) => {
    const rect = await evaluate(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); if (!e) return null;
      e.scrollIntoView({block: 'center'}); const r = e.getBoundingClientRect();
      return {x: r.left + scrollX, y: r.top + scrollY, width: r.width, height: r.height}; })()`);
    if (!rect) return false;
    await sleep(250);
    const width = fullWidth ? await evaluate("window.innerWidth") : rect.width + 2 * pad;
    await shot(file, { x: fullWidth ? 0 : Math.max(0, rect.x - pad), y: Math.max(0, rect.y - pad), width, height: rect.height + 2 * pad });
    return true;
  };
  const key = async (key, code = key, vk = 0, modifiers = 0) => {
    const text = key.length === 1 ? key : undefined;
    await send("Input.dispatchKeyEvent", { type: text ? "keyDown" : "rawKeyDown", key, code, windowsVirtualKeyCode: vk, modifiers, text });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key, code, windowsVirtualKeyCode: vk, modifiers });
    await sleep(120);
  };
  // Scrolls only when the element is outside the viewport, so in-place behavior can still be measured.
  const center = (selector) => evaluate(`(() => { const e = document.querySelector(${JSON.stringify(selector)}); if (!e) return null;
    let r = e.getBoundingClientRect(); if (r.bottom < 0 || r.top > innerHeight) { e.scrollIntoView({block: 'center', behavior: 'instant'}); r = e.getBoundingClientRect(); }
    return {x: r.left + r.width / 2, y: r.top + r.height / 2}; })()`);
  const click = async (selector) => {
    const point = await center(selector);
    if (!point) return false;
    for (const type of ["mousePressed", "mouseReleased"]) {
      await send("Input.dispatchMouseEvent", { type, x: point.x, y: point.y, button: "left", clickCount: 1 });
    }
    await sleep(250);
    return true;
  };
  const drag = async (selector, dx) => {
    const p = await center(selector);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: p.x, y: p.y, button: "left", clickCount: 1 });
    for (let i = 1; i <= 6; i++) await send("Input.dispatchMouseEvent", { type: "mouseMoved", x: p.x + (dx * i) / 6, y: p.y, button: "left", buttons: 1 });
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: p.x + dx, y: p.y, button: "left", clickCount: 1 });
    await sleep(300);
  };
  const swipe = async (selector, dx) => {
    const p = await center(selector);
    await send("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: p.x, y: p.y }] });
    for (let i = 1; i <= 6; i++) await send("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: [{ x: p.x + (dx * i) / 6, y: p.y }] });
    await send("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await sleep(300);
  };
  const tabUntil = async (predicate, limit = 80) => {
    for (let i = 0; i < limit; i++) {
      await send("Input.dispatchKeyEvent", { type: "rawKeyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      if (await evaluate(predicate)) return true;
    }
    return false;
  };
  const injected = [];
  const inject = async (source) => injected.push((await send("Page.addScriptToEvaluateOnNewDocument", { source })).identifier);
  const clearInjected = async () => { while (injected.length) await send("Page.removeScriptToEvaluateOnNewDocument", { identifier: injected.pop() }); };
  const media = (features = [], type = "") => send("Emulation.setEmulatedMedia", { media: type, features });

  const report = {};
  for (const dist of dists) {
    const root = resolve(dist);
    const pub = basename(dirname(root));
    const dir = join(outDir, pub);
    mkdirSync(dir, { recursive: true });
    const url = (name) => pathToFileURL(join(root, name)).href;
    const pages = readdirSync(root).filter((n) => n.endsWith(".html")).sort();
    const md = (name) => readFileSync(join(root, name.replace(/\.html$/, ".md")), "utf8");
    const checks = {};
    const details = {};
    log.remote.length = 0; log.console.length = 0; log.exceptions.length = 0;
    await media();

    // ---- Desktop: cover, navigation collapse with persistence.
    await viewport(1280, 900);
    await navigate(url("index.html"));
    await evaluate("localStorage.clear()");
    await navigate(url("index.html"));
    await loadLazy();
    checks["Alpine initialized from the bundled file"] = await evaluate("!!window.Alpine && document.documentElement.classList.contains('js')");
    checks["GSAP loaded from the bundled file"] = await evaluate("!!window.gsap && typeof gsap.fromTo === 'function'");
    checks["search index loaded from a bundled script"] = await evaluate("Array.isArray(window.DISTILL_SEARCH?.entries) && DISTILL_SEARCH.entries.length > 0");
    details.nav = await evaluate("[...document.querySelectorAll('.nav-list a')].map(a => [a.textContent, a.getAttribute('aria-current')])");
    checks["cover nav lists seven pages with Overview current"] = details.nav.length === 7 && details.nav[0][1] === "page";
    await shot(join(dir, "desktop-cover.png"));
    await click(".nav-close");
    details.collapsed = await evaluate("({cls: document.documentElement.classList.contains('nav-collapsed'), nav: getComputedStyle(document.getElementById('site-nav')).display, focus: document.activeElement.className, expanded: document.querySelector('.menu-button').getAttribute('aria-expanded')})");
    checks["desktop navigation collapses and focus moves to Show navigation"] = details.collapsed.cls && details.collapsed.nav === "none" && /menu-button/.test(details.collapsed.focus) && details.collapsed.expanded === "false";
    await navigate(url("article.html"));
    checks["collapsed navigation persists across pages"] = await evaluate("document.documentElement.classList.contains('nav-collapsed') && getComputedStyle(document.getElementById('site-nav')).display === 'none'");
    await shot(join(dir, "desktop-article-nav-collapsed.png"));
    checks["Copy Page button has the exact label"] = await evaluate("document.querySelector('.copy-page').textContent.trim() === 'Copy Page'");

    // ---- Script failure with a saved collapse and theme: navigation and content stay usable.
    await evaluate("localStorage.setItem('distill.theme', 'nord')");
    const failureState = "({ready: document.documentElement.classList.contains('ready'), collapsed: document.documentElement.classList.contains('nav-collapsed'), nav: (() => { const n = document.getElementById('site-nav'); const r = n.getBoundingClientRect(); const s = getComputedStyle(n); return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.left >= 0 && r.right <= innerWidth; })(), links: [...document.querySelectorAll('.nav-list a')].filter(a => a.getClientRects().length).length, jsOnlyShown: [...document.querySelectorAll('.js-only')].filter(e => getComputedStyle(e).display !== 'none').map(e => e.className), theme: document.documentElement.dataset.theme || '', paper: getComputedStyle(document.documentElement).backgroundColor, download: !!document.querySelector('a.download-md[download]')?.getClientRects().length, steps: [...document.querySelectorAll('.fig-sequence .step')].every(s => getComputedStyle(s).display !== 'none'), alpine: !!window.Alpine})";
    const logMark = [log.console.length, log.exceptions.length];
    details.blocked = {};
    for (const [label, blocked] of [["Alpine", ["*/vendor/alpine-3.17.4.min.js"]], ["article.js and Alpine", ["*/assets/article.js", "*/vendor/alpine-3.17.4.min.js"]], ["article.js", ["*/assets/article.js"]]]) {
      await send("Network.setBlockedURLs", { urls: blocked });
      await viewport(1280, 900);
      await navigate(url("article.html"));
      const desktop = await evaluate(failureState);
      await viewport(390, 844, true, 2);
      await navigate(url("article.html"));
      const mobile = await evaluate(failureState);
      if (label === "Alpine") {
        await shot(join(dir, "blocked-alpine-mobile.png"));
        await viewport(1280, 900);
        await navigate(url("article.html"));
        await shot(join(dir, "blocked-alpine-desktop.png"));
        await evaluate("document.querySelector('sup.cite a').scrollIntoView({block: 'center'})");
        await click("sup.cite a");
        details.blockedCite = await evaluate("({hash: location.hash, target: !!document.getElementById(location.hash.slice(1)), panel: document.getElementById('evidence-panel').hidden})");
        checks["blocked Alpine: citations stay ordinary links to the references"] = /^#ref-\d+$/.test(details.blockedCite.hash) && details.blockedCite.target && details.blockedCite.panel;
      }
      details.blocked[label] = { desktop, mobile };
      checks[`blocked ${label} with a saved collapse: navigation visible on desktop and mobile, no dead controls`] =
        [desktop, mobile].every((v) => !v.ready && !v.collapsed && v.nav && v.links === 7 && !v.jsOnlyShown.length && v.download && v.steps);
      checks[`blocked ${label}: the saved theme still applies`] = [desktop, mobile].every((v) => v.theme === "nord" && v.paper === "rgb(46, 52, 64)");
    }
    await send("Network.setBlockedURLs", { urls: [] });
    // Blocking article.js leaves Alpine to report its missing components; those are expected here only.
    details.blockedConsole = log.console.splice(logMark[0]).concat(log.exceptions.splice(logMark[1]));
    await viewport(1280, 900);
    await navigate(url("article.html"));
    await evaluate("localStorage.removeItem('distill.theme')");
    checks["with scripts restored the saved collapse applies again"] = await evaluate("document.documentElement.classList.contains('ready') && document.documentElement.classList.contains('nav-collapsed') && getComputedStyle(document.getElementById('site-nav')).display === 'none'");
    await navigate(url("article.html"));
    await click(".menu-button");
    checks["Show navigation restores the sidebar"] = await evaluate("!document.documentElement.classList.contains('nav-collapsed') && getComputedStyle(document.getElementById('site-nav')).display !== 'none' && localStorage.getItem('distill.nav') === null");

    // ---- Article: existing interactions.
    await navigate(url("article.html"));
    await loadLazy();
    await shot(join(dir, "desktop-top.png"));
    await fullShot(join(dir, "desktop-full.png"));
    const hasSeq = await evaluate("!!document.querySelector('.fig-sequence')");
    if (hasSeq) {
      const visible = () => evaluate("[...document.querySelectorAll('.fig-sequence .step')].map(s => getComputedStyle(s).display !== 'none')");
      details.initial = await visible();
      checks["stepper shows only the first step initially"] = details.initial[0] && details.initial.slice(1).every((v) => !v);
      await evaluate("(() => { const b = [...document.querySelectorAll('.fig-sequence .step-button')].find(b => b.textContent.trim() === 'Next'); b.click(); b.click(); b.click(); })()");
      await sleep(300);
      details.afterNext = await visible();
      details.counter = await evaluate("document.querySelector('.fig-sequence .counter').textContent");
      checks["Next steps through to the last step and stops"] = details.afterNext[details.afterNext.length - 1] &&
        details.afterNext.filter(Boolean).length === 1 && details.counter.startsWith(`${details.afterNext.length} /`);
      await elementShot(join(dir, "desktop-stepper-last.png"), ".fig-sequence");
    }
    if (await evaluate("!!document.querySelector('article details')")) {
      await evaluate("document.querySelector('article details summary').click()");
      await sleep(200);
      checks["details expands on click"] = await evaluate("document.querySelector('article details').open");
      await elementShot(join(dir, "desktop-details.png"), "article details");
    }
    if (await evaluate("!!document.querySelector('[x-data=zoom] .frame')")) {
      await evaluate("document.querySelector('[x-data=zoom] .frame').click()");
      await sleep(300);
      checks["figure zoom opens a modal dialog with focus inside"] = await evaluate("!!document.activeElement?.closest('dialog[open]')");
      await key("Escape", "Escape", 27);
      checks["Escape closes the figure dialog"] = await evaluate("!document.querySelector('dialog[open]')");
    }
    await evaluate("document.activeElement?.blur(); window.scrollTo(0, 0)");
    const focusStyle = "(() => { const e = document.activeElement; const s = getComputedStyle(e); return {tag: e.tagName, cls: e.className, inCite: !!e.closest('.cite, .rail'), outline: s.outlineStyle + ' ' + s.outlineWidth}; })()";
    await tabUntil("!!document.activeElement.closest('.cite, .rail')");
    details.focusOutline = await evaluate(focusStyle);
    checks["keyboard focus is visible on citation links"] = details.focusOutline.inCite && !details.focusOutline.outline.startsWith("none");
    await evaluate("document.activeElement.scrollIntoView({block: 'center'})");
    await sleep(150);
    await shot(join(dir, "desktop-keyboard-focus.png"));

    // ---- Evidence panel: opens in place, keeps URL and scroll, returns focus.
    await evaluate("document.querySelector('sup.cite a').scrollIntoView({block: 'center'})");
    await sleep(700);
    const before = await evaluate("({y: Math.round(scrollY), hash: location.hash})");
    await click("sup.cite a");
    // Measure final layout, not an intermediate GSAP transform on a busy browser.
    for (let i = 0; i < 20 && await evaluate("!!window.gsap?.isTweening(document.getElementById('evidence-panel'))"); i++) {
      await sleep(50);
    }
    details.panel = await evaluate("(() => { const p = document.getElementById('evidence-panel'); const r = p.getBoundingClientRect(); return {open: !p.hidden, y: Math.round(scrollY), hash: location.hash, focus: document.activeElement.id, right: Math.round(innerWidth - r.right), width: Math.round(r.width), text: p.textContent.slice(0, 400)}; })()");
    checks["citation opens the evidence panel without navigating or scrolling"] = details.panel.open && details.panel.hash === before.hash && Math.abs(details.panel.y - before.y) <= 2 && details.panel.focus === "evidence-title";
    checks["evidence panel shows the transcript segment or source"] = /Transcript segment|External source/.test(details.panel.text);
    checks["desktop evidence is a right-hand panel"] = details.panel.right === 0 && details.panel.width < 500;
    await sleep(300);
    await shot(join(dir, "desktop-evidence-panel.png"));
    await key("Escape", "Escape", 27);
    checks["Escape closes the panel and returns focus to the citation"] = await evaluate("document.getElementById('evidence-panel').hidden && !!document.activeElement.closest('sup.cite')");

    // ---- Copy Page: clipboard, legacy copy, manual fallback. Always the full Markdown twin.
    const articleMd = md("article.html");
    await evaluate("window.scrollTo(0, 0)");
    await click(".copy-page");
    await sleep(300);
    details.clipboard = await evaluate("navigator.clipboard.readText().then(t => ({ok: true, length: t.length, text: t}), e => ({ok: false, error: String(e)}))");
    details.copyStatus = await evaluate("document.getElementById('copy-status').textContent");
    checks["Copy Page writes the full Markdown to the real clipboard"] = details.clipboard.ok && details.clipboard.text === articleMd && /Copied/.test(details.copyStatus);
    details.clipboard.text = undefined;
    checks["Copy Page label confirms the copy"] = await evaluate("document.querySelector('.copy-page').textContent.trim() === 'Copied'");
    await elementShot(join(dir, "desktop-copy-status.png"), ".toolbar", 4);
    await evaluate("navigator.clipboard.writeText = () => Promise.reject(new Error('denied'))");
    await click(".copy-page");
    await sleep(300);
    details.legacy = await evaluate("({status: document.getElementById('copy-status').textContent, open: document.getElementById('md-source').open})");
    checks["denied Clipboard API falls back to execCommand copy"] = /Copied/.test(details.legacy.status) && !details.legacy.open;
    await evaluate("document.execCommand = () => false");
    await click(".copy-page");
    await sleep(400);
    details.manual = await evaluate("(() => { const a = document.getElementById('page-markdown'); return {open: document.getElementById('md-source').open, focused: document.activeElement === a, selected: a.selectionEnd - a.selectionStart, length: a.value.length, status: document.getElementById('copy-status').textContent, label: document.querySelector('.copy-page').textContent.trim(), inView: (() => { const r = a.getBoundingClientRect(); return r.top >= 0 && r.top < innerHeight; })()}; })()");
    checks["blocked copying selects the full Markdown for manual copy"] = details.manual.open && details.manual.focused && details.manual.selected === articleMd.length && /Ctrl\+C/.test(details.manual.status) && details.manual.inView && details.manual.label === "Copy Page";
    await shot(join(dir, "desktop-copy-manual-fallback.png"));

    // ---- Reveals: once-only, subtle, never leave content hidden; hash targets arrive visible.
    await navigate(url("article.html"));
    details.revealStart = await evaluate("[...document.querySelectorAll('.reveal')].map(e => getComputedStyle(e).opacity)");
    checks["no section is hidden before it is revealed"] = details.revealStart.every((o) => Number(o) === 1);
    await evaluate("window.scrollTo(0, document.body.scrollHeight)");
    await sleep(900);
    await evaluate("window.scrollTo(0, 0)");
    await sleep(900);
    details.revealEnd = await evaluate("[...document.querySelectorAll('.reveal')].map(e => [getComputedStyle(e).opacity, e.style.transform || ''])");
    checks["reveals finish fully opaque with no lingering transform"] = details.revealEnd.every(([o, t]) => Number(o) === 1 && t === "");
    const lastSection = await evaluate("document.querySelector('article > section.reveal:last-of-type')?.id");
    if (lastSection) {
      await navigate(url("article.html") + "#" + lastSection, 60);
      details.hashOpacity = await evaluate(`getComputedStyle(document.getElementById(${JSON.stringify(lastSection)})).opacity`);
      checks["hash target is visible immediately"] = Number(details.hashOpacity) === 1;
    }

    // ---- Search: keyboard shortcut, bundled index, ordinary links that land on visible targets.
    await navigate(url("article.html"));
    await key("/", "Slash", 191);
    checks["/ opens the search dialog with focus in the field"] = await evaluate("document.getElementById('search-dialog').open && document.activeElement.id === 'search-input'");
    const term = await evaluate("(() => { const e = DISTILL_SEARCH.entries.find(e => e[0].startsWith('transcript-')); return e[3].split(/\\s+/).filter(w => w.length > 4)[0].replace(/[^\\p{L}\\p{N}]/gu, ''); })()");
    await send("Input.insertText", { text: term });
    await sleep(400);
    details.search = await evaluate("({summary: document.getElementById('search-count').textContent, hrefs: [...document.querySelectorAll('.search-results a')].map(a => a.getAttribute('href')), marks: document.querySelectorAll('.search-results mark').length})");
    details.searchTerm = term;
    checks["search finds transcript text and highlights it"] = details.search.hrefs.some((h) => h.startsWith("transcript-")) && details.search.marks > 0;
    await shot(join(dir, "desktop-search.png"));
    const hit = details.search.hrefs.find((h) => h.startsWith("transcript-")) || details.search.hrefs[0] || "";
    if (hit) await evaluate(`document.querySelector('.search-results a[href="${hit}"]').click()`);
    await sleep(900);
    details.searchLanding = await evaluate("({path: location.pathname.split('/').pop(), hash: location.hash, visible: (() => { const t = document.getElementById(decodeURIComponent(location.hash.slice(1))); if (!t) return false; const r = t.getBoundingClientRect(); return Number(getComputedStyle(t).opacity) === 1 && r.bottom > 0 && r.top < innerHeight; })()})");
    checks["search result link lands on a visible target"] = !!hit && hit.startsWith(details.searchLanding.path) && details.searchLanding.visible;
    await shot(join(dir, "desktop-search-landing.png"));
    const cjk = await evaluate("(() => { const e = DISTILL_SEARCH.entries.find(e => / Original$/.test(e[1]) && /[\\u3040-\\u30ff\\u4e00-\\u9fff]{3}/.test(e[3])); return e ? e[3].match(/[\\u3040-\\u30ff\\u4e00-\\u9fff]{3}/)[0] : null; })()");
    if (cjk) {
      await key("/", "Slash", 191);
      await evaluate("(() => { const i = document.getElementById('search-input'); i.value = ''; i.dispatchEvent(new Event('input')); })()");
      await send("Input.insertText", { text: cjk });
      await sleep(300);
      details.cjkSearch = { term: cjk, hrefs: await evaluate("[...document.querySelectorAll('.search-results a')].map(a => a.getAttribute('href'))") };
      checks["search finds original-language (CJK) transcript text"] = details.cjkSearch.hrefs.some((h) => /\.original\.html#seg-/.test(h));
      await shot(join(dir, "desktop-search-cjk.png"));
      await key("Escape", "Escape", 27);
    }

    // ---- Transcript filters do not change what Copy Page copies.
    const transcript = pages.find((p) => /^transcript-.*(?<!\.original)\.html$/.test(p));
    await navigate(url(transcript));
    await evaluate("(() => { const s = document.querySelector('.filter-bar select'); s.value = 'true'; s.dispatchEvent(new Event('change')); })()");
    await sleep(200);
    details.filter = await evaluate("({shown: document.querySelectorAll('#seg-list [data-filter-item]:not([hidden])').length, total: document.querySelectorAll('#seg-list [data-filter-item]').length, summary: document.querySelector('.filter-count').textContent})");
    checks["transcript filter narrows the list"] = details.filter.shown < details.filter.total;
    await evaluate("window.__copied = null; navigator.clipboard.writeText = (t) => { window.__copied = t; return Promise.resolve(); }");
    await click(".copy-page");
    checks["filtered page still copies its full Markdown"] = (await evaluate("window.__copied")) === md(transcript);
    await shot(join(dir, "desktop-transcript-filtered.png"));

    // ---- Search to a segment the filter hides, on the same page and with the same hash: it is revealed.
    const hiddenSeg = await evaluate("document.querySelector('#seg-list .seg[hidden]')?.id || null");
    if (hiddenSeg) {
      const href = `${transcript}#${hiddenSeg}`;
      await navigate(url(transcript) + "#" + hiddenSeg);
      await evaluate("(() => { const s = document.querySelector('.filter-bar select'); s.value = 'true'; s.dispatchEvent(new Event('change')); })()");
      await sleep(200);
      details.filterSearch = { before: await evaluate(`({hidden: document.getElementById(${JSON.stringify(hiddenSeg)}).hidden, hash: location.hash})`) };
      const words = await evaluate(`DISTILL_SEARCH.entries.find(e => e[0] === ${JSON.stringify(href)})[3].split(/\\s+/).slice(0, 4).join(' ')`);
      await key("/", "Slash", 191);
      await send("Input.insertText", { text: words });
      await sleep(400);
      details.filterSearch.words = words;
      details.filterSearch.found = await click(`.search-results a[href="${href}"]`);
      await sleep(600);
      // Scroll positions round to pixels; Linux font metrics can leave the target at -0.375px.
      // Allow only subpixel rounding, not a genuinely offscreen target.
      details.filterSearch.after = await evaluate(`(() => { const t = document.getElementById(${JSON.stringify(hiddenSeg)}); const r = t.getBoundingClientRect(); return {hidden: t.hidden, inView: Math.round(r.top) >= 0 && r.top < innerHeight && r.bottom > 0, dialog: document.getElementById('search-dialog').open, hash: location.hash, summary: document.querySelector('.filter-count').textContent, select: document.querySelector('.filter-bar select').value}; })()`);
      checks["search to a filtered-out segment on the same page reveals and shows it"] = details.filterSearch.before.hidden && details.filterSearch.found &&
        !details.filterSearch.after.hidden && details.filterSearch.after.inView && !details.filterSearch.after.dialog && details.filterSearch.after.select === "" && /cleared/.test(details.filterSearch.after.summary);
      await shot(join(dir, "desktop-search-reveals-filtered.png"));
      await evaluate("(() => { const s = document.querySelector('.filter-bar select'); s.value = 'true'; s.dispatchEvent(new Event('change')); })()");
      await navigate(url("article.html"));
      await navigate(url(transcript) + "#" + hiddenSeg);
      await evaluate("(() => { const s = document.querySelector('.filter-bar select'); s.value = 'true'; s.dispatchEvent(new Event('change')); location.hash = ''; })()");
      await sleep(200);
      await evaluate(`location.hash = ${JSON.stringify(hiddenSeg)}`);
      await sleep(400);
      checks["a hash link to a filtered-out segment reveals it"] = await evaluate(`(() => { const t = document.getElementById(${JSON.stringify(hiddenSeg)}); const r = t.getBoundingClientRect(); return !t.hidden && Math.round(r.top) >= 0 && r.top < innerHeight && r.bottom > 0; })()`);
    }

    // ---- Gallery viewer: buttons, keyboard, zoom, pan, drag swipe, focus return, filters.
    await navigate(url("gallery.html"));
    await loadLazy();
    await fullShot(join(dir, "desktop-gallery.png"));
    const count = await evaluate("document.querySelectorAll('.g-item').length");
    if (count) {
      await click(".g-open");
      await sleep(400);
      details.viewer = await evaluate("(() => { const d = document.querySelector('dialog.viewer'); const i = d.querySelector('.viewer-stage img'); return {open: d.open, loaded: i.complete && i.naturalWidth > 0, count: d.querySelector('.viewer-count').textContent, focus: document.activeElement.textContent, caption: d.querySelector('.viewer-caption').textContent.slice(0, 200)}; })()");
      details.zoomDuringEntrance = await evaluate(`(async () => {
        const d = document.querySelector('dialog.viewer'); const img = d.querySelector('.viewer-stage img');
        d.close(); await new Promise(r => setTimeout(r, 100));
        document.querySelector('.g-open').click(); await new Promise(r => setTimeout(r, 40));
        const tweening = !!window.gsap && gsap.isTweening(img);
        d.dispatchEvent(new KeyboardEvent('keydown', {key: '+', bubbles: true}));
        await new Promise(r => setTimeout(r, 700));
        return {tweening, transform: img.style.transform, scale: d.querySelector('.viewer-scale').textContent, opacity: getComputedStyle(img).opacity};
      })()`);
      checks["zooming during the entrance animation keeps the zoom"] = details.zoomDuringEntrance.tweening && /scale\(1\.5\)/.test(details.zoomDuringEntrance.transform) && details.zoomDuringEntrance.scale === "150%" && details.zoomDuringEntrance.opacity === "1";
      await key("0", "Digit0", 48);
      checks["gallery viewer opens with the image, counter, and provenance"] = details.viewer.open && details.viewer.loaded && details.viewer.count === `1 of ${count}` && /untouched|reconstruction/.test(details.viewer.caption);
      const counter = () => evaluate("document.querySelector('.viewer-count').textContent");
      const scale = () => evaluate("document.querySelector('.viewer-scale').textContent");
      if (count > 1) {
        await key("ArrowRight", "ArrowRight", 39);
        checks["ArrowRight shows the next image"] = (await counter()) === `2 of ${count}`;
        await key("ArrowLeft", "ArrowLeft", 37);
      }
      await key("+", "Equal", 187);
      await key("+", "Equal", 187);
      details.zoomed = await scale();
      checks["+ zooms in"] = details.zoomed === "225%";
      const before = await evaluate("document.querySelector('.viewer-stage img').style.transform");
      await key("ArrowLeft", "ArrowLeft", 37);
      await drag(".viewer-stage", -120);
      details.panned = { before, after: await evaluate("document.querySelector('.viewer-stage img').style.transform"), counter: await counter() };
      checks["arrows and drag pan while zoomed instead of changing image"] = details.panned.after !== before && details.panned.counter === `1 of ${count}`;
      await shot(join(dir, "desktop-viewer-zoomed.png"));
      await key("0", "Digit0", 48);
      checks["0 fits the image"] = (await scale()) === "100%";
      if (count > 1) {
        await drag(".viewer-stage", -200);
        checks["drag-swipe at fit shows the next image"] = (await counter()) === `2 of ${count}`;
      }
      await shot(join(dir, "desktop-viewer.png"));
      await key("Escape", "Escape", 27);
      checks["Escape closes the viewer and returns focus to the thumbnail"] = await evaluate("!document.querySelector('dialog.viewer').open && document.activeElement.classList.contains('g-open')");
      const kinds = await evaluate("[...document.querySelectorAll('.filter-bar select[data-facet=kind] option')].map(o => o.value).filter(Boolean)");
      if (kinds.length > 1) {
        await evaluate(`(() => { const s = document.querySelector('.filter-bar select[data-facet=kind]'); s.value = ${JSON.stringify(kinds[kinds.length - 1])}; s.dispatchEvent(new Event('change')); })()`);
        await sleep(200);
        details.galleryFilter = await evaluate("document.querySelectorAll('.g-item:not([hidden])').length");
        checks["gallery kind filter narrows the grid"] = details.galleryFilter > 0 && details.galleryFilter < count;
      }
    }

    // ---- Themes: choice, persistence, print stays house light, storage failure is harmless.
    await navigate(url("article.html"));
    await evaluate("(() => { const s = document.getElementById('theme-select'); s.value = 'dracula'; s.dispatchEvent(new Event('change')); })()");
    await sleep(200);
    details.dracula = await evaluate("getComputedStyle(document.documentElement).backgroundColor");
    checks["choosing Dracula applies its background"] = details.dracula === "rgb(40, 42, 54)";
    await navigate(url("gallery.html"));
    checks["theme choice persists across pages"] = await evaluate("document.documentElement.dataset.theme === 'dracula' && document.getElementById('theme-select').value === 'dracula'");
    await navigate(url("article.html"));
    await loadLazy();
    await shot(join(dir, "theme-dracula.png"));
    for (const theme of ["solarized-light", "catppuccin-mocha", "gruvbox-light", "tokyo-night-night"]) {
      await evaluate(`(() => { const s = document.getElementById('theme-select'); s.value = '${theme}'; s.dispatchEvent(new Event('change')); })()`);
      await sleep(150);
      await shot(join(dir, `theme-${theme}.png`));
    }
    await media([], "print");
    details.printBackground = await evaluate("getComputedStyle(document.documentElement).getPropertyValue('--paper').trim()");
    checks["print uses house light colors whatever the theme"] = details.printBackground === "#f4f5f7";
    await media();
    await evaluate("localStorage.setItem('distill.theme', 'no-such-theme')");
    await navigate(url("article.html"));
    checks["an unknown saved theme falls back to the default"] = await evaluate("!document.documentElement.hasAttribute('data-theme') && localStorage.getItem('distill.theme') === null");
    await media([{ name: "prefers-color-scheme", value: "dark" }]);
    checks["system dark preference selects house dark by default"] = (await evaluate("getComputedStyle(document.documentElement).getPropertyValue('--paper').trim()")) === "#0e1015";
    await shot(join(dir, "theme-system-dark.png"));
    await media();
    await inject("(() => { const fail = () => { throw new DOMException('blocked', 'SecurityError'); }; Object.defineProperty(window, 'localStorage', { get: fail, configurable: true }); })()");
    const exceptionsBefore = log.exceptions.length;
    await navigate(url("article.html"));
    await evaluate("(() => { const s = document.getElementById('theme-select'); s.value = 'nord'; s.dispatchEvent(new Event('change')); })()");
    await sleep(150);
    checks["blocked storage: page works and themes still apply for the page"] = log.exceptions.length === exceptionsBefore && await evaluate("!!window.Alpine && document.documentElement.dataset.theme === 'nord'");
    await clearInjected();

    // ---- GSAP failure and reduced motion: everything visible, controls still work.
    await inject("Object.defineProperty(window, 'gsap', { get() { return undefined; }, set() {}, configurable: false });");
    await navigate(url("article.html"));
    await evaluate("window.scrollTo(0, document.body.scrollHeight)");
    await sleep(500);
    details.noGsap = await evaluate("({gsap: typeof window.gsap, alpine: !!window.Alpine, opacities: [...document.querySelectorAll('.reveal')].map(e => getComputedStyle(e).opacity)})");
    await evaluate("window.scrollTo(0, 0)");
    await click("sup.cite a");
    checks["without GSAP the page is fully visible and interactive"] = details.noGsap.gsap === "undefined" && details.noGsap.alpine && details.noGsap.opacities.every((o) => Number(o) === 1) && await evaluate("!document.getElementById('evidence-panel').hidden");
    await clearInjected();
    await media([{ name: "prefers-reduced-motion", value: "reduce" }]);
    await navigate(url("article.html"));
    await evaluate("window.scrollTo(0, document.body.scrollHeight)");
    await sleep(500);
    details.reduced = await evaluate("({tweens: window.gsap ? gsap.globalTimeline.getChildren(true, true, false).length : -1, inline: [...document.querySelectorAll('.reveal')].filter(e => e.style.opacity || e.style.transform).length})");
    await evaluate("window.scrollTo(0, 0)");
    await click("sup.cite a");
    details.reducedPanel = await evaluate("({open: !document.getElementById('evidence-panel').hidden, style: document.getElementById('evidence-panel').style.cssText})");
    checks["reduced motion: no tweens, no inline animation styles"] = details.reduced.tweens === 0 && details.reduced.inline === 0 && details.reducedPanel.open && !details.reducedPanel.style;
    await media();

    // ---- Mobile: no overflow on any page, overlay navigation, bottom sheet, touch swipe.
    await viewport(390, 844, true, 2);
    await send("Emulation.setTouchEmulationEnabled", { enabled: true, maxTouchPoints: 5 });
    details.mobileOverflow = {};
    details.textareaMismatch = [];
    for (const name of pages) {
      await navigate(url(name), 300);
      details.mobileOverflow[name] = await evaluate("document.documentElement.scrollWidth - window.innerWidth");
      if ((await evaluate("document.getElementById('page-markdown').value")) !== md(name)) details.textareaMismatch.push(name);
    }
    checks["every page's Markdown textarea value equals its downloaded .md byte for byte"] = !details.textareaMismatch.length;
    checks["mobile layout has no horizontal overflow on any page"] = Object.values(details.mobileOverflow).every((v) => v <= 1);
    await navigate(url("index.html"));
    await loadLazy();
    await shot(join(dir, "mobile-cover.png"));
    await navigate(url("article.html"));
    await loadLazy();
    await shot(join(dir, "mobile-top.png"));
    await fullShot(join(dir, "mobile-full.png"));
    await click(".menu-button");
    await sleep(300);
    details.mobileNav = await evaluate("({open: document.documentElement.classList.contains('nav-open'), focusInNav: !!document.activeElement.closest('#site-nav'), inert: document.getElementById('page').inert, expanded: document.querySelector('.menu-button').getAttribute('aria-expanded')})");
    checks["mobile menu opens an overlay with focus inside and the page inert"] = details.mobileNav.open && details.mobileNav.focusInNav && details.mobileNav.inert && details.mobileNav.expanded === "true";
    await shot(join(dir, "mobile-nav-open.png"));
    let escaped = false;
    for (let i = 0; i < 25; i++) {
      await key("Tab", "Tab", 9);
      if (!(await evaluate("!!document.activeElement.closest('#site-nav')"))) { escaped = true; break; }
    }
    checks["Tab stays inside the open mobile menu"] = !escaped;
    await key("Escape", "Escape", 27);
    checks["Escape closes the mobile menu and returns focus to Menu"] = await evaluate("!document.documentElement.classList.contains('nav-open') && document.activeElement.classList.contains('menu-button') && !document.getElementById('page').inert");
    await evaluate("document.querySelector('sup.cite a').scrollIntoView({block: 'center'})");
    await sleep(700);
    await click("sup.cite a");
    await sleep(300);
    details.sheet = await evaluate("(() => { const r = document.getElementById('evidence-panel').getBoundingClientRect(); return {top: Math.round(r.top), bottom: Math.round(r.bottom), width: Math.round(r.width), vh: innerHeight, vw: innerWidth}; })()");
    checks["mobile evidence is a bottom sheet"] = details.sheet.bottom === details.sheet.vh && details.sheet.top > details.sheet.vh * 0.2 && details.sheet.width === details.sheet.vw;
    await shot(join(dir, "mobile-evidence-sheet.png"));
    if (hasSeq) await elementShot(join(dir, "mobile-stepper.png"), ".fig-sequence", 8, true);
    await navigate(url("gallery.html"));
    await loadLazy();
    if (count > 1) {
      await click(".g-open");
      await sleep(400);
      await swipe(".viewer-stage", -180);
      details.touchSwipe = await evaluate("document.querySelector('.viewer-count').textContent");
      checks["touch swipe shows the next image"] = details.touchSwipe === `2 of ${count}`;
      await shot(join(dir, "mobile-viewer.png"));
      await key("Escape", "Escape", 27);
    }
    await send("Emulation.setTouchEmulationEnabled", { enabled: false });

    // ---- Print emulation of the PDF source (article.html?print=1).
    await viewport(1280, 900);
    await navigate(url("article.html") + "?print=1");
    await loadLazy();
    await media([], "print");
    await sleep(300);
    details.print = await evaluate("({steps: [...document.querySelectorAll('.fig-sequence .step')].map(s => getComputedStyle(s).display), details: [...document.querySelectorAll('article details')].every(d => d.open), chrome: ['site-nav', 'evidence-panel'].map(id => getComputedStyle(document.getElementById(id)).display).concat([getComputedStyle(document.querySelector('.toolbar')).display, getComputedStyle(document.querySelector('.md-source')).display]), opacity: [...document.querySelectorAll('.reveal')].every(e => getComputedStyle(e).opacity === '1')})");
    checks["print shows every sequence step"] = details.print.steps.every((d) => d !== "none");
    checks["print opens every details block"] = details.print.details;
    checks["print hides navigation, toolbar, panel, and Markdown source"] = details.print.chrome.every((d) => d === "none");
    checks["print shows every section fully opaque"] = details.print.opacity;
    await fullShot(join(dir, "print-full.png"));
    await media();

    // ---- No JavaScript: everything readable, ordinary links, no dead controls.
    await send("Emulation.setScriptExecutionDisabled", { value: true });
    details.noJs = {};
    for (const name of pages) {
      await navigate(url(name), 200);
      details.noJs[name] = await evaluate("({navVisible: getComputedStyle(document.getElementById('site-nav')).display !== 'none', jsOnlyHidden: [...document.querySelectorAll('.js-only')].every(e => getComputedStyle(e).display === 'none'), steps: [...document.querySelectorAll('.fig-sequence .step')].every(s => getComputedStyle(s).display !== 'none'), download: !!document.querySelector('a.download-md[download]'), markdown: !!document.getElementById('page-markdown'), filteredHidden: document.querySelectorAll('[data-filter-item][hidden]').length})");
    }
    checks["without JavaScript every page shows nav, steps, Markdown, and download, with no dead controls"] =
      Object.values(details.noJs).every((v) => v.navVisible && v.jsOnlyHidden && v.steps && v.download && v.markdown && v.filteredHidden === 0);
    await navigate(url("index.html"), 200);
    await shot(join(dir, "nojs-cover.png"));
    await navigate(url("article.html"), 200);
    await shot(join(dir, "nojs-article.png"));
    await viewport(390, 844, true, 2);
    await navigate(url("article.html"), 200);
    await shot(join(dir, "nojs-mobile-article.png"));
    details.noJsCite = await evaluate("document.querySelector('sup.cite a').getAttribute('href')");
    checks["without JavaScript citations are ordinary links to references"] = /^#ref-\d+$/.test(details.noJsCite) && await evaluate(`!!document.getElementById(${JSON.stringify(details.noJsCite.slice(1))})`);
    await send("Emulation.setScriptExecutionDisabled", { value: false });
    await viewport(1280, 900);

    await navigate(url("brief.html"));
    await loadLazy();
    await fullShot(join(dir, "brief-full.png"));
    details.briefHeadings = await evaluate("[...document.querySelectorAll('h2, h3')].map(h => h.textContent.trim())");
    checks["brief separates what sources establish from proposals"] =
      details.briefHeadings.some((h) => /establish/i.test(h)) && details.briefHeadings.some((h) => /propose/i.test(h));
    for (const name of ["references.html", "glossary.html", "transcripts.html", transcript, transcript.replace(".html", ".original.html")]) {
      await navigate(url(name));
      await shot(join(dir, `desktop-${name.replace(".html", "")}.png`));
    }

    details.remoteRequests = [...log.remote];
    details.console = [...log.console];
    details.exceptions = [...log.exceptions];
    checks["no remote requests"] = log.remote.length === 0;
    checks["no console errors or exceptions"] = log.console.length === 0 && log.exceptions.length === 0;
    await evaluate("localStorage.clear()");
    report[pub] = { checks, details };
  }
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  cdp.close();
  const failed = Object.entries(report).flatMap(([p, r]) => Object.entries(r.checks).filter(([, ok]) => !ok).map(([n]) => `${p}: ${n}`));
  if (failed.length) console.error("failed:\n" + failed.join("\n"));
  process.exit(0);
}

main().catch((error) => { console.error(error); process.exit(1); });
