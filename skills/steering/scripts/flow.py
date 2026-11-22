#!/usr/bin/env python3
"""Flow metrics and a Monte Carlo forecast from tracker data.

  python3 flow.py metrics  FILE [--today YYYY-MM-DD] [--json]
  python3 flow.py forecast FILE [--today YYYY-MM-DD] [--remaining N] [--due YYYY-MM-DD]
                                [--seed N] [--runs N] [--weeks N] [--json]

FILE is either a tracker-neutral flow.json:

  {"contract": "flow/v1",
   "items": [{"id": "S-1", "title": "optional", "started": "2026-11-02", "finished": "2026-11-05"},
             {"id": "S-2", "started": "2026-11-03", "finished": null}]}

or the output of this export of the stories and bugs a backlog synced by `syncing` has (a JSON
list; the comma in the label search means "either label"):

  gh issue list --repo OWNER/REPO --state all --limit 1000 \\
    --search 'label:"type:story","type:bug"' --json number,createdAt,closedAt,stateReason

gh lists 30 issues unless --limit is given, and a search returns at most 1000; an export of exactly
1000 issues prints a warning on stderr, because it may be cut short. For GitHub, an
issue starts when it is created and finishes when it is closed, so its cycle time is the time from
creation to close. When an issue has the stateReason field, a closure other than COMPLETED (for
example NOT_PLANNED or DUPLICATE) is not finished work: the issue is removed, neither finished nor
open, and counted as "removed". Export only finished work as "finished" in a flow.json.
Timestamps count by their UTC date. --today is a UTC date and defaults to today's UTC date.

Definitions:
- Cycle time: calendar days from start to finish, both days counted (same day = 1).
- Age of an open item: calendar days from start to --today, both days counted.
- Work in progress: items started and not finished.
- Weekly throughput: items finished per week, Monday to Sunday. The history runs from the week of
  the first start to the last complete week before --today; a week with no finish counts 0. The
  current week is shown apart and is not used for the forecast.
- Percentiles use the nearest rank: the value at rank ceil(p / 100 * n) of the sorted values.
- Aging: open items older than the 85th percentile of cycle time.
- Forecast: each run draws weekly throughput at random from the history (the last --weeks complete
  weeks, default all) until --remaining items (default: the open items) are done. It reports the
  50th, 85th and 95th percentile weeks, the dates (--today plus that many weeks) and, with --due,
  the chance to finish by that date. Without --seed a seed is drawn and printed, so a run can be
  repeated. A history with no complete week, or no finish in it, refuses to forecast.

Exits 0 on success. Exits 1 and prints one line per problem in the input, or the refusal.
Standard library only.
"""

import argparse
import datetime as dt
import json
import math
import random
import sys

FIELDS = {"id", "title", "started", "finished"}
EXPORT = ("gh issue list --repo OWNER/REPO --state all --limit 1000 "
          "--search 'label:\"type:story\",\"type:bug\"' --json number,createdAt,closedAt,stateReason")
SEARCH_CAP = 1000  # gh issue list --search returns at most this many issues
LIMIT = 520  # weeks; a run that needs more than ten years refuses rather than guesses


def rows_in(path):
    """The number of issues in a gh list export; None for a flow.json or unreadable input."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return len(data) if isinstance(data, list) else None


def day(value):
    """A UTC date from 'YYYY-MM-DD' or an ISO timestamp; None when it is not one."""
    if not isinstance(value, str):
        return None
    try:
        if len(value) == 10:
            return dt.date.fromisoformat(value)
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is not None:
        stamp = stamp.astimezone(dt.timezone.utc)
    return stamp.date()


def load(path, today):
    """Items as (id, started, finished or None) and the problems found."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as error:
        return [], [f"input: cannot read {path} as JSON ({error})"], 0
    if isinstance(data, list):
        rows, problems, removed = github(data)
    elif isinstance(data, dict) and data.get("contract") == "flow/v1" and isinstance(data.get("items"), list):
        rows, problems = neutral(data)
        removed = 0
    else:
        return [], ["input: expected a flow.json with \"contract\": \"flow/v1\" and \"items\", "
                    f"or the output of {EXPORT}"], 0
    items, seen = [], set()
    for ident, start, finish in rows:
        if ident in seen:
            problems.append(f"{ident}: the id appears more than once")
            continue
        seen.add(ident)
        if start is None:
            continue  # already reported
        if finish is not None and finish < start:
            problems.append(f"{ident}: finished {finish} before it started {start}")
        elif start > today or (finish is not None and finish > today):
            problems.append(f"{ident}: a date is after --today {today} (UTC dates)")
        else:
            items.append((ident, start, finish))
    return items, problems, removed


def neutral(data):
    rows, problems = [], []
    for n, item in enumerate(data["items"], 1):
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
            problems.append(f"item {n}: needs a text \"id\"")
            continue
        ident = item["id"]
        for field in sorted(set(item) - FIELDS):
            problems.append(f"{ident}: unknown field \"{field}\" (allowed: {', '.join(sorted(FIELDS))})")
        start, finish = day(item.get("started")), day(item.get("finished"))
        if start is None:
            problems.append(f"{ident}: \"started\" must be a date, YYYY-MM-DD")
        if item.get("finished") is not None and finish is None:
            problems.append(f"{ident}: \"finished\" must be a date, YYYY-MM-DD, or null")
            start = None
        rows.append((ident, start, finish))
    return rows, problems


def github(data):
    rows, problems, removed = [], [], 0
    for n, issue in enumerate(data, 1):
        if not isinstance(issue, dict) or not isinstance(issue.get("number"), int):
            problems.append(f"issue {n}: needs a \"number\"; run {EXPORT}")
            continue
        ident = f"#{issue['number']}"
        start, finish = day(issue.get("createdAt")), day(issue.get("closedAt"))
        if start is None:
            problems.append(f"{ident}: \"createdAt\" must be a timestamp")
        if issue.get("closedAt") is not None and finish is None:
            problems.append(f"{ident}: \"closedAt\" must be a timestamp or null")
            start = None
        if finish is not None and "stateReason" in issue and issue["stateReason"] != "COMPLETED":
            removed += 1  # closed as not planned, duplicate or similar: not finished work
            continue
        rows.append((ident, start, finish))
    return rows, problems, removed


def nearest_rank(values, p):
    ordered = sorted(values)
    return ordered[max(1, math.ceil(p / 100 * len(ordered))) - 1]


def monday(date):
    return date - dt.timedelta(days=date.weekday())


def metrics(items, today, removed=0):
    this_week = monday(today)
    weeks = []
    if items:
        week = monday(min(start for _, start, _ in items))
        while week < this_week:
            weeks.append(week)
            week += dt.timedelta(days=7)
    done = [finish for _, _, finish in items if finish is not None]
    counts = {week: 0 for week in weeks + [this_week]}
    for finish in done:
        if monday(finish) in counts:
            counts[monday(finish)] += 1
    cycle = [(finish - start).days + 1 for _, start, finish in items if finish is not None]
    found = {
        "today": today.isoformat(),
        "items": len(items),
        "finished": len(done),
        "wip": len(items) - len(done),
        "removed": removed,
        "throughput": [{"week": w.isoformat(), "finished": counts[w]} for w in weeks],
        "this_week": {"week": this_week.isoformat(), "finished": counts[this_week]},
        "cycle_time": {"count": len(cycle)},
    }
    if cycle:
        p85 = nearest_rank(cycle, 85)
        found["cycle_time"].update(p50=nearest_rank(cycle, 50), p85=p85)
        open_items = [(ident, (today - start).days + 1) for ident, start, finish in items if finish is None]
        found["aging"] = [{"id": ident, "age": age}
                          for ident, age in sorted(open_items, key=lambda x: -x[1]) if age > p85]
    return found


def forecast(found, today, remaining, runs, seed, last, due):
    history = [w["finished"] for w in found["throughput"]]
    if last:
        history = history[-last:]
    if not history:
        return None, "forecast refused: no complete week of history before --today"
    if not any(history):
        return None, f"forecast refused: no item finished in the {len(history)} complete weeks of history"
    rng = random.Random(seed)
    results = []
    for _ in range(runs):
        done, weeks = 0, 0
        while done < remaining:
            done += rng.choice(history)
            weeks += 1
            if weeks > LIMIT:
                return None, f"forecast refused: a run needs more than {LIMIT} weeks; the history is too thin"
        results.append(weeks)
    weeks = {f"p{p}": nearest_rank(results, p) for p in (50, 85, 95)}
    out = {
        "today": today.isoformat(), "remaining": remaining, "runs": runs, "seed": seed,
        "history_weeks": len(history), "weeks": weeks,
        "dates": {k: (today + dt.timedelta(weeks=v)).isoformat() for k, v in weeks.items()},
    }
    if due:
        by_due = sum(1 for w in results if today + dt.timedelta(weeks=w) <= due)
        out.update(due=due.isoformat(), chance_by_due=round(100 * by_due / runs),
                   p85_by_due=today + dt.timedelta(weeks=weeks["p85"]) <= due)
    return out, None


def days(n):
    return f"{n} day" if n == 1 else f"{n} days"


def show_metrics(found):
    ct = found["cycle_time"]
    lines = [f"Flow on {found['today']}: {found['items']} items, {found['finished']} finished, "
             f"{found['wip']} in progress."]
    if found["removed"]:
        lines.append(f"Removed: {found['removed']} closed without being completed (not planned, duplicate).")
    if found["throughput"]:
        lines.append("Weekly throughput (week starting Monday: finished):")
        lines += [f"  {w['week']}: {w['finished']}" for w in found["throughput"]]
    else:
        lines.append("Weekly throughput: no complete week of history.")
    lines.append(f"  {found['this_week']['week']}: {found['this_week']['finished']} (this week, not complete)")
    if ct["count"]:
        lines.append(f"Cycle time over {ct['count']} finished items: 50th percentile {days(ct['p50'])}, "
                     f"85th percentile {days(ct['p85'])}.")
        if found["aging"]:
            lines.append(f"Aging (open longer than {days(ct['p85'])}):")
            lines += [f"  {a['id']}: {days(a['age'])}" for a in found["aging"]]
        else:
            lines.append(f"Aging: no open item is older than {days(ct['p85'])}.")
    else:
        lines.append("Cycle time: not measured; no item has finished.")
        lines.append("Aging: not measured; it needs a cycle time.")
    return "\n".join(lines)


def show_forecast(out):
    w, d = out["weeks"], out["dates"]
    lines = [f"Forecast on {out['today']} for {out['remaining']} items: {out['runs']} runs, seed {out['seed']}, "
             f"drawn from {out['history_weeks']} complete weeks.",
             *(f"  {k[1:]}th percentile: {w[k]} weeks, by {d[k]}" for k in ("p50", "p85", "p95"))]
    if "due" in out:
        verdict = "on or before" if out["p85_by_due"] else "after"
        lines.append(f"Due {out['due']}: {out['chance_by_due']}% of runs finish by then; "
                     f"the 85th percentile date is {verdict} it.")
    lines.append("A forecast is a probability from past throughput, not a commitment.")
    return "\n".join(lines)


def date_arg(value):
    found = day(value) if len(value) == 10 else None
    if found is None:
        raise argparse.ArgumentTypeError(f"{value!r} is not a date, YYYY-MM-DD")
    return found


def positive(value):
    if not value.isdigit() or int(value) < 1:
        raise argparse.ArgumentTypeError(f"{value!r} is not a whole number above 0")
    return int(value)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("metrics", "forecast"):
        cmd = sub.add_parser(name)
        cmd.add_argument("file")
        cmd.add_argument("--today", type=date_arg, default=dt.datetime.now(dt.timezone.utc).date(),
                         help="a UTC date, YYYY-MM-DD (default: today's UTC date)")
        cmd.add_argument("--json", action="store_true", help="print JSON instead of text")
    cast = sub.choices["forecast"]
    cast.add_argument("--remaining", type=lambda v: 0 if v == "0" else positive(v),
                      help="items left to finish (default: the open items)")
    cast.add_argument("--due", type=date_arg, help="milestone due date to compare with")
    cast.add_argument("--seed", type=int, help="random seed; the same seed repeats the result")
    cast.add_argument("--runs", type=positive, default=10000)
    cast.add_argument("--weeks", type=positive, help="use only the last N complete weeks")
    args = parser.parse_args(argv)

    items, problems, removed = load(args.file, args.today)
    if rows_in(args.file) == SEARCH_CAP:
        print(f"warning: the export has exactly {SEARCH_CAP} issues, the most a gh search returns; it may be "
              "cut short. Export again in date ranges (for example created:<2026-01-01) and merge them.",
              file=sys.stderr)
    if problems:
        print("\n".join(problems))
        return 1
    found = metrics(items, args.today, removed)
    if args.command == "metrics":
        print(json.dumps(found, indent=2) if args.json else show_metrics(found))
        return 0
    remaining = found["wip"] if args.remaining is None else args.remaining
    seed = random.SystemRandom().randrange(10**6) if args.seed is None else args.seed
    out, refusal = forecast(found, args.today, remaining, args.runs, seed, args.weeks, args.due)
    if refusal:
        print(refusal)
        return 1
    print(json.dumps(out, indent=2) if args.json else show_forecast(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
