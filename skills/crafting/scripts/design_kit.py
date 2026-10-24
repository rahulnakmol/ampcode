#!/usr/bin/env python3
"""Design workspace helper for the crafting skill.

Commands (run from the project root; --dir defaults to .design):
  init  --surfaces web,ios     create the workspace files that do not exist yet
  log   --tool T --note N      price a research call and refuse it when over budget (exit 2)
  spend                        show research spend against the budget
  check                        verify journeys and that every touchpoint has every required state
                               (exit 1 on gaps)
  tools PATH                   lint an MCP tool list: each tool has a description with a "Not for"
                               clause, an inputSchema, and all four annotation hints (exit 1 on gaps)

Standard library only. Makes no network calls.
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Interactive surfaces share the core states; static media (print, social, documents, and so on)
# have no loading or error moment, so their "states" are the variants that must be designed.
CORE_STATES = ("ideal", "empty", "loading", "error")
SURFACE_STATES = {
    # Terminal
    "cli": CORE_STATES + ("non-tty", "no-color", "json"),
    "tui": CORE_STATES + ("narrow-terminal", "no-color", "keyboard-focus"),
    # Screens
    "web": CORE_STATES + ("keyboard-focus", "narrow", "dark"),
    "ios": CORE_STATES + ("offline", "large-text", "dark"),
    "android": CORE_STATES + ("offline", "large-text", "dark"),
    "macos": CORE_STATES + ("keyboard-focus", "narrow-window", "dark"),
    "windows": CORE_STATES + ("keyboard-focus", "narrow-window", "dark"),
    # Ambient
    "watch": CORE_STATES + ("glance", "always-on", "large-text"),
    "tv": CORE_STATES + ("focus", "safe-area", "large-text"),
    "car": CORE_STATES + ("driving", "night", "voice-only"),
    "spatial": CORE_STATES + ("gaze-focus", "immersive", "large-text"),
    "kiosk": CORE_STATES + ("idle", "timeout", "reach-range"),
    "device": CORE_STATES + ("setup", "offline", "firmware-update"),
    # Conversation and messaging
    "chat": CORE_STATES + ("streaming", "tool-call", "interrupted"),
    "voice": CORE_STATES + ("no-match", "no-input", "barge-in"),
    "notification": ("ideal", "grouped", "actioned", "dark"),
    "email": ("ideal", "dark", "images-off", "narrow", "plain-text"),
    "sms": ("ideal", "long-message", "opt-out"),
    # Agents
    "api": CORE_STATES + ("validation-error", "rate-limited", "auth-error"),
    "mcp": CORE_STATES + ("validation-error", "auth-error", "large-result"),
    "a2a": CORE_STATES + ("input-required", "cancelled", "auth-error"),
    "webhook": ("ideal", "retry", "signature-failure", "replay"),
    "agent-docs": ("ideal", "ambiguity", "outdated"),
    # Social, physical, and media
    "social": ("ideal", "square", "vertical", "link-preview", "sound-off", "safe-zone"),
    "print": ("ideal", "bleed", "grayscale", "long-copy", "preflight"),
    "packaging": ("ideal", "dieline", "shelf-distance", "regulatory-panel", "preflight"),
    "signage": ("ideal", "viewing-distance", "low-light", "sequence", "tactile"),
    "presentation": ("ideal", "projector", "handout", "speaker-notes"),
    "video": ("ideal", "sound-off", "vertical", "thumbnail"),
    "document": ("ideal", "print", "screen-reader", "long-content"),
    "dataviz": CORE_STATES + ("color-blind", "dense", "table-alternative"),
}
SURFACES = tuple(SURFACE_STATES)
INTERACTION_FIELDS = ("trigger", "feedback", "motion", "reduced_motion")

# Parallel Task API, USD per run (docs.parallel.ai pricing, 2026-10-24). "-fast" variants cost the same.
TASK_PRICES = {"lite": 0.005, "base": 0.01, "core": 0.025, "core2x": 0.05, "pro": 0.10,
               "ultra": 0.30, "ultra2x": 0.60, "ultra4x": 1.20, "ultra8x": 2.40}
# Parallel Search list prices, USD per call or per URL; the OAuth free tier may make these $0.
SEARCH_PRICES = {"parallel-search.web_search": 0.005, "parallel-search.web_fetch": 0.001}
PAID_TASK_TOOLS = ("parallel-task.createDeepResearch", "parallel-task.createTaskGroup")
DEFAULT_BUDGET = {"usd": 0.30, "firecrawl_credits": 15, "mobbin_searches": 10}
ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


def fail(message, code=1):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def read_json(path):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        fail(f"{path} does not exist; run init first")
    except json.JSONDecodeError as error:
        fail(f"{path} is not valid JSON: {error}")


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def required_states(surface):
    return SURFACE_STATES[surface]


def cmd_init(args):
    surfaces = [s.strip() for s in args.surfaces.split(",") if s.strip()]
    unknown = [s for s in surfaces if s not in SURFACES]
    if not surfaces or unknown:
        fail(f"--surfaces must list some of {', '.join(SURFACES)}; got {args.surfaces!r}")
    root = Path(args.dir)
    for sub in ("research/img", "mockups", "board"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    created = []
    touchpoints = root / "touchpoints.json"
    if not touchpoints.exists():
        write_json(touchpoints, {"surfaces": surfaces, "journeys": [], "touchpoints": []})
        created.append(touchpoints)
    ledger = root / "ledger.json"
    if not ledger.exists():
        write_json(ledger, {"budget": dict(DEFAULT_BUDGET), "entries": []})
        created.append(ledger)
    for path in created:
        print(f"created {path}")
    print("required states per touchpoint:")
    for surface in surfaces:
        print(f"  {surface}: {', '.join(required_states(surface))}")


def totals(entries):
    result = {"usd": 0.0, "firecrawl_credits": 0, "mobbin_searches": 0}
    for entry in entries:
        result["usd"] += entry.get("usd", 0)
        result["firecrawl_credits"] += entry.get("credits", 0)
        result["mobbin_searches"] += entry.get("mobbin_searches", 0)
    result["usd"] = round(result["usd"], 4)
    return result


def price(args):
    if args.count < 1:
        fail("--count must be at least 1")
    entry = {"tool": args.tool, "count": args.count, "usd": 0.0, "credits": 0, "mobbin_searches": 0}
    if args.tool in PAID_TASK_TOOLS:
        processor = re.sub(r"-fast$", "", args.processor or "")
        if processor not in TASK_PRICES:
            fail(f"{args.tool} needs --processor, one of {', '.join(TASK_PRICES)} (optionally -fast)")
        entry["processor"] = args.processor
        entry["usd"] = round(TASK_PRICES[processor] * args.count, 4)
    elif args.tool in SEARCH_PRICES:
        entry["usd"] = round(SEARCH_PRICES[args.tool] * args.count, 4)
    elif args.tool.startswith("firecrawl."):
        entry["credits"] = args.credits if args.credits is not None else args.count
    elif args.tool.startswith("mobbin.search_"):
        entry["mobbin_searches"] = args.count
    return entry


def cmd_log(args):
    path = Path(args.dir) / "ledger.json"
    ledger = read_json(path)
    entry = price(args)
    budget = {**DEFAULT_BUDGET, **ledger.get("budget", {})}
    after = totals(ledger.get("entries", []) + [entry])
    over = [key for key in budget if after[key] > budget[key] + 1e-9]
    if over and not args.approved:
        details = ", ".join(f"{key} {after[key]} > {budget[key]}" for key in over)
        fail(f"over budget ({details}); ask the user, then rerun with --approved", code=2)
    entry.update(note=args.note, at=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    if over:
        entry["approved_over_budget"] = True
    ledger.setdefault("entries", []).append(entry)
    write_json(path, ledger)
    print(f"logged {args.tool}: ${entry['usd']:.3f}, {entry['credits']} credits, "
          f"{entry['mobbin_searches']} Mobbin searches; total ${after['usd']:.3f} of ${budget['usd']:.2f}")


def cmd_spend(args):
    ledger = read_json(Path(args.dir) / "ledger.json")
    budget = {**DEFAULT_BUDGET, **ledger.get("budget", {})}
    spent = totals(ledger.get("entries", []))
    print(f"Parallel (USD): ${spent['usd']:.3f} of ${budget['usd']:.2f}")
    print(f"Firecrawl credits: {spent['firecrawl_credits']} of {budget['firecrawl_credits']}")
    print(f"Mobbin searches: {spent['mobbin_searches']} of {budget['mobbin_searches']}")
    print(f"Logged calls: {len(ledger.get('entries', []))}")


# Published image assets ship with alt text, so every non-skipped state records it.
ALT_SURFACES = ("social",)


def check_touchpoints(root):
    data = read_json(root / "touchpoints.json")
    gaps = []
    surfaces = data.get("surfaces", [])
    for surface in surfaces:
        if surface not in SURFACES:
            gaps.append(f"unknown surface {surface!r} in surfaces")
    touchpoints = data.get("touchpoints", [])
    if not touchpoints:
        gaps.append("no touchpoints defined")
    seen, covered, skipped = set(), 0, 0
    for index, touchpoint in enumerate(touchpoints):
        tid = touchpoint.get("id", f"#{index}")
        if not isinstance(tid, str) or not ID.match(tid):
            gaps.append(f"{tid}: id must match {ID.pattern}")
        if tid in seen:
            gaps.append(f"{tid}: duplicate id")
        seen.add(tid)
        surface = touchpoint.get("surface")
        if surface not in SURFACES:
            gaps.append(f"{tid}: surface must be one of {', '.join(SURFACES)}")
            continue
        if surfaces and surface not in surfaces:
            gaps.append(f"{tid}: surface {surface} is not listed in surfaces")
        if not str(touchpoint.get("job", "")).strip():
            gaps.append(f"{tid}: missing job")
        states = touchpoint.get("states", {})
        for state in required_states(surface):
            if state not in states:
                gaps.append(f"{tid}: missing required state {state!r} (mock it or add a skip reason)")
        for state, spec in states.items():
            spec = spec if isinstance(spec, dict) else {}
            if str(spec.get("skip", "")).strip():
                skipped += 1
            elif not spec.get("mockup"):
                gaps.append(f"{tid}.{state}: needs a mockup path or a skip reason")
            elif not (root / spec["mockup"]).is_file():
                gaps.append(f"{tid}.{state}: mockup {spec['mockup']} not found under {root}")
            else:
                covered += 1
            if surface in ALT_SURFACES and not str(spec.get("skip", "")).strip() \
                    and not str(spec.get("alt", "")).strip():
                gaps.append(f"{tid}.{state}: needs alt text (\"alt\") for this asset")
        for position, interaction in enumerate(touchpoint.get("interactions", [])):
            name = interaction.get("id", f"#{position}")
            for field in INTERACTION_FIELDS:
                if not str(interaction.get(field, "")).strip():
                    gaps.append(f"{tid}: interaction {name} is missing {field}")
    for surface in surfaces:
        if surface in SURFACES and not any(t.get("surface") == surface for t in touchpoints):
            gaps.append(f"surface {surface} has no touchpoints")
    for index, journey in enumerate(data.get("journeys", [])):
        jid = journey.get("id", f"#{index}")
        for field in ("actor", "goal"):
            if not str(journey.get(field, "")).strip():
                gaps.append(f"journey {jid}: missing {field}")
        steps = journey.get("steps", [])
        if not steps:
            gaps.append(f"journey {jid}: no steps")
        for step in steps:
            if step not in seen:
                gaps.append(f"journey {jid}: step {step!r} is not a touchpoint id")
    return gaps, len(touchpoints), covered, skipped


def cmd_check(args):
    gaps, count, covered, skipped = check_touchpoints(Path(args.dir))
    for gap in gaps:
        print(f"gap: {gap}")
    print(f"{count} touchpoints, {covered} states mocked, {skipped} skipped with reasons, {len(gaps)} gaps")
    sys.exit(1 if gaps else 0)


TOOL_HINTS = ("readOnlyHint", "destructiveHint", "idempotentHint", "openWorldHint")


def lint_tools(data):
    tools = data.get("tools", data) if isinstance(data, dict) else data
    if not isinstance(tools, list) or not tools:
        return ["no tools found (expected a list or an object with a \"tools\" list)"]
    gaps = []
    for index, tool in enumerate(tools):
        name = tool.get("name", f"#{index}")
        if not re.search(r"\bnot for\b", str(tool.get("description", "")), re.IGNORECASE):
            gaps.append(f"{name}: description needs a 'Not for X; use Y' clause")
        if not isinstance(tool.get("inputSchema"), dict):
            gaps.append(f"{name}: missing inputSchema")
        annotations = tool.get("annotations") or {}
        for hint in TOOL_HINTS:
            if not isinstance(annotations.get(hint), bool):
                gaps.append(f"{name}: annotations.{hint} must be true or false")
    return gaps


def cmd_tools(args):
    gaps = lint_tools(read_json(Path(args.path)))
    for gap in gaps:
        print(f"gap: {gap}")
    print(f"{len(gaps)} gaps")
    sys.exit(1 if gaps else 0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default=".design", help="design workspace directory (default .design)")
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="create workspace files that do not exist yet")
    init.add_argument("--surfaces", required=True, help=f"comma-separated: {', '.join(SURFACES)}")
    init.set_defaults(func=cmd_init)

    log = commands.add_parser("log", help="price and record a research call before making it")
    log.add_argument("--tool", required=True, help="module.function, e.g. parallel-task.createDeepResearch")
    log.add_argument("--processor", help="Parallel Task processor, e.g. pro, base, lite-fast")
    log.add_argument("--count", type=int, default=1, help="runs, rows, searches, or URLs (default 1)")
    log.add_argument("--credits", type=int, help="Firecrawl credits (default: --count)")
    log.add_argument("--note", required=True, help="the question this call answers")
    log.add_argument("--approved", action="store_true", help="the user approved going over budget")
    log.set_defaults(func=cmd_log)

    spend = commands.add_parser("spend", help="show research spend against the budget")
    spend.set_defaults(func=cmd_spend)

    check = commands.add_parser("check", help="verify state coverage; exit 1 on gaps")
    check.set_defaults(func=cmd_check)

    tools = commands.add_parser("tools", help="lint an MCP tool list; exit 1 on gaps")
    tools.add_argument("path", help="tools.json: a list of tools or an object with a tools list")
    tools.set_defaults(func=cmd_tools)

    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
