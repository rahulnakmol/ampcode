#!/usr/bin/env node
// Drives a real Chromium-family browser over the DevTools protocol (no npm dependencies) to check and
// capture rendered distilling-videos publications opened via file://.
//
// Usage: node capture.mjs BROWSER OUT_DIR DIST_DIR [DIST_DIR...]
// Writes OUT_DIR/<publication>/*.png and OUT_DIR/report.json ({publication: {checks, details}}).
// Any request that is not file: or data: is recorded as a remote request (the pages must make none).
import { spawn } from "node:child_process";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
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
  cdp.on((msg) => {
    if (msg.method === "Network.requestWillBeSent") {
      const url = msg.params.request.url;
      if (!/^(file|data|about|blob):/.test(url)) log.remote.push(url);
    } else if (msg.method === "Runtime.consoleAPICalled" && ["error", "warning", "assert"].includes(msg.params.type)) {
      log.console.push(msg.params.args.map((a) => a.value ?? a.description).join(" "));
    } else if (msg.method === "Runtime.exceptionThrown") {
      log.exceptions.push(msg.params.exceptionDetails.exception?.description ?? msg.params.exceptionDetails.text);
    }
  });
  await send("Page.enable");
  await send("Runtime.enable");
  await send("Network.enable");

  const evaluate = async (expression) => {
    const r = await send("Runtime.evaluate", { expression, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + " " + expression.slice(0, 80));
    return r.result.value;
  };
  const navigate = async (url) => {
    let loaded;
    const done = new Promise((r) => { loaded = r; });
    cdp.on((msg) => { if (msg.method === "Page.loadEventFired") loaded(); });
    await send("Page.navigate", { url });
    await Promise.race([done, sleep(10000)]);
    await sleep(600);
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
    // Full-width clips for mobile: figures may bleed past their column, and a tight clip would cut them.
    const width = fullWidth ? await evaluate("window.innerWidth") : rect.width + 2 * pad;
    await shot(file, { x: fullWidth ? 0 : Math.max(0, rect.x - pad), y: Math.max(0, rect.y - pad), width, height: rect.height + 2 * pad });
    return true;
  };

  const report = {};
  for (const dist of dists) {
    const pub = basename(dirname(resolve(dist)));
    const dir = join(outDir, pub);
    mkdirSync(dir, { recursive: true });
    const url = pathToFileURL(join(resolve(dist), "index.html")).href;
    const checks = {};
    const details = {};
    log.remote.length = 0; log.console.length = 0; log.exceptions.length = 0;

    await viewport(1280, 900);
    await navigate(url);
    await loadLazy();
    checks["Alpine initialized from the bundled file"] = await evaluate("!!window.Alpine && document.documentElement.classList.contains('js')");
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
      await evaluate("document.querySelector('.fig-sequence').focus?.()");
      await elementShot(join(dir, "desktop-stepper-last.png"), ".fig-sequence");
      await evaluate("document.querySelector('.fig-sequence .thumb').click()");
      await sleep(200);
    }
    const hasDetails = await evaluate("!!document.querySelector('details')");
    if (hasDetails) {
      await evaluate("document.querySelector('details summary').click()");
      await sleep(200);
      checks["details expands on click"] = await evaluate("document.querySelector('details').open");
      await elementShot(join(dir, "desktop-details.png"), "details");
    }
    const hasZoom = await evaluate("!!document.querySelector('[x-data=zoom] .frame')");
    if (hasZoom) {
      await evaluate("document.querySelector('[x-data=zoom] .frame').click()");
      await sleep(300);
      checks["zoom opens a modal dialog"] = await evaluate("!!document.querySelector('dialog[open]')");
      checks["focus moves into the dialog"] = await evaluate("!!document.activeElement?.closest('dialog[open]')");
      await shot(join(dir, "desktop-zoom.png"));
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
      await sleep(200);
      checks["Escape closes the dialog"] = await evaluate("!document.querySelector('dialog[open]')");
    }
    // Real Tab key presses (so :focus-visible applies) until a citation or timecode link has focus.
    await evaluate("document.activeElement?.blur(); window.scrollTo(0, 0)");
    const focusStyle = "(() => { const e = document.activeElement; const s = getComputedStyle(e); return {tag: e.tagName, cls: e.className, inCite: !!e.closest('.cite, .rail'), outline: s.outlineStyle + ' ' + s.outlineWidth, shadow: s.boxShadow}; })()";
    for (let i = 0; i < 60; i++) {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab", windowsVirtualKeyCode: 9 });
      details.focusOutline = await evaluate(focusStyle);
      if (details.focusOutline.inCite) break;
    }
    checks["keyboard focus is visible on citation links"] = details.focusOutline.inCite &&
      (!details.focusOutline.outline.startsWith("none") || details.focusOutline.shadow !== "none");
    if (details.focusOutline.inCite) {
      await evaluate("document.activeElement.scrollIntoView({block: 'center'})");
      await sleep(150);
      await shot(join(dir, "desktop-keyboard-focus.png"));
    }

    await viewport(390, 844, true, 2);
    await navigate(url);
    await loadLazy();
    details.mobileOverflow = await evaluate("document.documentElement.scrollWidth - window.innerWidth");
    checks["mobile layout has no horizontal overflow"] = details.mobileOverflow <= 1;
    await shot(join(dir, "mobile-top.png"));
    await fullShot(join(dir, "mobile-full.png"));
    if (hasSeq) {
      await elementShot(join(dir, "mobile-stepper.png"), ".fig-sequence", 8, true);
    }

    await viewport(1280, 900);
    await navigate(url + "?print=1");
    await loadLazy();
    await send("Emulation.setEmulatedMedia", { media: "print" });
    await sleep(300);
    details.printSteps = await evaluate("[...document.querySelectorAll('.fig-sequence .step')].map(s => getComputedStyle(s).display)");
    checks["print shows every sequence step"] = details.printSteps.every((d) => d !== "none");
    checks["print opens every details block"] = await evaluate("[...document.querySelectorAll('details')].every(d => d.open)");
    await fullShot(join(dir, "print-full.png"));
    await send("Emulation.setEmulatedMedia", { media: "" });

    await send("Emulation.setScriptExecutionDisabled", { value: true });
    await navigate(url);
    details.noJsSteps = await evaluate("[...document.querySelectorAll('.fig-sequence .step')].map(s => getComputedStyle(s).display)");
    checks["without JavaScript every step is visible"] = details.noJsSteps.every((d) => d !== "none");
    await send("Emulation.setScriptExecutionDisabled", { value: false });

    await navigate(pathToFileURL(join(resolve(dist), "brief.html")).href);
    await loadLazy();
    await fullShot(join(dir, "brief-full.png"));
    details.briefHeadings = await evaluate("[...document.querySelectorAll('h2, h3')].map(h => h.textContent.trim())");
    checks["brief separates what sources establish from proposals"] =
      details.briefHeadings.some((h) => /establish/i.test(h)) && details.briefHeadings.some((h) => /propose/i.test(h));

    details.remoteRequests = [...log.remote];
    details.console = [...log.console];
    details.exceptions = [...log.exceptions];
    checks["no remote requests"] = log.remote.length === 0;
    checks["no console errors or exceptions"] = log.console.length === 0 && log.exceptions.length === 0;
    report[pub] = { checks, details };
  }
  writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2));
  cdp.close();
  const failed = Object.entries(report).flatMap(([p, r]) => Object.entries(r.checks).filter(([, ok]) => !ok).map(([n]) => `${p}: ${n}`));
  if (failed.length) console.error("failed:\n" + failed.join("\n"));
  process.exit(0);
}

main().catch((error) => { console.error(error); process.exit(1); });
