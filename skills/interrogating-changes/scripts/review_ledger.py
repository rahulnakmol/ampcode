#!/usr/bin/env python3
"""Check a review ledger and give a verdict tied to the exact patch.

  python3 review_ledger.py check <ledger.json> [--repo <path>]
  python3 review_ledger.py verdict --base <rev> --head <rev> [--ledger <ledger.json>] [--repo <path>]

check: exits 0 and prints "pass" when the ledger follows rules L1 to L9 in
../reference/ledger.md. Otherwise exits 1 and prints each problem as "<rule>: <what to fix>".

verdict: prints the candidate's patch ID (`git diff <base>..<head> | git patch-id --verbatim`)
and one verdict: "pass", "changes needed", "stale" (the ledger reviewed another patch),
"ledger invalid" or "not reviewed" (no ledger). Exits 0 only on "pass".

Standard library only. The check proves that each quote is in the named file at the reviewed
revision and that its origin matches the lines the change touched. It cannot prove that the reviewer read
callers, guards and tests, or that a run's output is real: those stay the reviewer's evidence.
"""

import argparse
import json
import re
import subprocess
import sys

FIELDS = ("id", "lens", "severity", "origin", "location", "quote", "problem", "evidence", "status")
LENSES = ("correctness", "security", "data and privacy", "concurrency and state", "tests")
SEVERITIES = ("Blocker", "Major", "Nit")
ORIGINS = ("regression", "pre-existing")
STATUSES = ("open", "fixed", "declined")
DISPOSITIONS = ("fixed", "replanned", "filed")
STABLE = ("problem", "lens", "severity", "origin")  # a reused ID keeps these
BLOCKING = ("Blocker", "Major")
CAP, RAISED_CAP = 3, 5
LOCATION = re.compile(r"^(?P<path>[^:\s][^:]*):(?P<start>[1-9]\d*)(?:-(?P<end>[1-9]\d*))?$")


def git(repo, *args, stdin=None):
    """stdout of a git command, or None when git fails."""
    run = subprocess.run(["git", "-C", repo, *args], input=stdin, capture_output=True, text=True)
    return run.stdout if run.returncode == 0 else None


def commit(repo, rev):
    out = git(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    return out.strip() if out else None


def diff(repo, *args):
    return git(repo, "diff", "--no-color", "--no-ext-diff", "--src-prefix=a/", "--dst-prefix=b/", *args)


def patch_id(repo, base, head):
    """The verbatim patch ID of base..head, '' for an empty diff, None when git fails.

    --verbatim keeps whitespace, so re-indenting code (moving a line out of an `if`) changes it.
    """
    text = diff(repo, f"{base}..{head}")
    if text is None:
        return None
    out = git(repo, "patch-id", "--verbatim", stdin=text)
    return out.split()[0] if out and out.strip() else ("" if out is not None else None)


def show(repo, rev, path):
    out = subprocess.run(["git", "-C", repo, "show", f"{rev}:{path}"], capture_output=True)
    return out.stdout.decode("utf-8", "replace") if out.returncode == 0 else None


def changed_lines(repo, base, head):
    """{path at head: head line numbers the change touched}, with renames followed.

    A touched line is an added line, or a line on either side of a deletion, so a removed
    guard counts against the lines around the gap.
    """
    touched, path = {}, None
    for line in (diff(repo, "-U0", "-M", base, head) or "").splitlines():
        if line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else None
        elif line.startswith("@@") and path:
            m = re.match(r"^@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if not m:
                continue
            removed, start, added = int(m[1] or 1), int(m[2]), int(m[3] or 1)
            lines = range(start, start + added) if added else (range(start, start + 2) if removed else ())
            touched.setdefault(path, set()).update(lines)
    return touched


def quote_lines(content, quote):
    """(first, last) line numbers of every place quote occurs in content."""
    spans, start = [], content.find(quote)
    while start != -1:
        first = content.count("\n", 0, start) + 1
        spans.append((first, first + quote.count("\n")))
        start = content.find(quote, start + 1)
    return spans


def check_finding(repo, rnd, finding, add, proof=None):
    """Check one finding; proof is the round whose head proves it (the round itself by default)."""
    where = f"round {rnd['round']} finding {finding.get('id') or '?'}"
    rnd = proof or rnd
    missing = [f for f in FIELDS if not isinstance(finding.get(f), str) or not finding[f].strip()]
    for field in missing:
        add("L2", f"{where}: missing {field!r}")
    for field, allowed in (("lens", LENSES), ("severity", SEVERITIES), ("origin", ORIGINS), ("status", STATUSES)):
        if field not in missing and finding[field] not in allowed:
            add("L2", f"{where}: {field!r} is {finding[field]!r}, not one of {', '.join(allowed)}")
    if "evidence" not in missing and not re.match(r"^(run|read): \S", finding["evidence"]):
        add("L2", f"{where}: 'evidence' must start 'run: ' (a command and what it showed) or 'read: ' (what was read)")
    if finding.get("status") == "declined" and not (
            finding.get("severity") == "Nit" or (finding.get("origin") == "pre-existing" and finding.get("filed"))):
        add("L7", f"{where}: declined only a Nit, or a pre-existing finding with 'filed' naming where it is filed")
    if "location" in missing or "quote" in missing:
        return
    match = LOCATION.match(finding["location"])
    if not match:
        add("L2", f"{where}: 'location' {finding['location']!r} is not path:line or path:start-end")
        return
    path, quote = match["path"], finding["quote"].strip()
    start, end = int(match["start"]), int(match["end"] or match["start"])
    if path not in rnd.get("scope", []):
        add("L3", f"{where}: {path} is not in the round's scope (files read)")
    if not (rnd.get("_head") and rnd.get("_base")):
        return
    content = show(repo, rnd["_head"], path)
    spans = quote_lines(content, quote) if content is not None else []
    here = [(a, b) for a, b in spans if a <= end and start <= b]
    if not spans:
        add("L4", f"{where}: not proven: the quote is not in {path} at head {rnd['head']}")
    elif not here:
        add("L4", f"{where}: not proven: the quote is in {path} at head, but not at {finding['location']}")
    if here and finding.get("origin") in ORIGINS:
        touched = changed_lines(repo, rnd["_base"], rnd["_head"]).get(path, set())
        changed = any(a <= n <= b for a, b in here for n in touched)
        if finding["origin"] == "regression" and not changed:
            add("L5", f"{where}: a regression, but its lines at head are unchanged since base {rnd['base']}: label it pre-existing, or quote the changed lines")
        if finding["origin"] == "pre-existing" and changed:
            add("L5", f"{where}: pre-existing, but its lines at head were changed by this change: label it a regression")


def latest(rounds, upto):
    """{id: finding} with each ID's last entry in rounds[:upto]."""
    state = {}
    for rnd in rounds[:upto]:
        for finding in rnd.get("findings") or []:
            if isinstance(finding, dict) and finding.get("id"):
                state[finding["id"]] = finding
    return state


def blocking(state):
    return [f for f in state.values() if f.get("status") == "open" and f.get("severity") in BLOCKING]


def check(ledger, repo):
    problems = []
    add = lambda rule, message: problems.append(f"{rule}: {message}")
    if not isinstance(ledger, dict) or not isinstance(ledger.get("rounds"), list) or not ledger["rounds"]:
        return ["L1: the ledger is an object with a non-empty 'rounds' list"]
    cap = ledger.get("cap", CAP)
    if cap not in (CAP, RAISED_CAP):
        add("L1", f"'cap' is {cap!r}: use {CAP}, or {RAISED_CAP} when the calling contract says so")
    elif cap == RAISED_CAP and not str(ledger.get("contract") or "").strip():
        add("L1", f"a cap of {RAISED_CAP} needs 'contract' naming the calling contract that sets it")
    rounds = ledger["rounds"]
    first, last_open = {}, {}  # ID -> (first entry, its round); ID -> round where it was last open
    for index, rnd in enumerate(rounds, 1):
        if not isinstance(rnd, dict):
            add("L1", f"round {index} is not an object")
            rounds[index - 1] = rnd = {}
        if rnd.get("round") != index:
            add("L1", f"round {index}: 'round' is {rnd.get('round')!r}; number rounds 1, 2, 3 in order")
        rnd["round"] = index
        for key in ("base", "head"):
            resolved = commit(repo, rnd[key]) if isinstance(rnd.get(key), str) and rnd[key] else None
            if not resolved:
                add("L1", f"round {index}: {key!r} {rnd.get(key)!r} is not a commit in {repo}")
            rnd[f"_{key}"] = resolved
        if rnd["_base"] and rnd["_head"]:
            actual = patch_id(repo, rnd["_base"], rnd["_head"])
            if rnd.get("patch_id") != actual:
                add("L1", f"round {index}: 'patch_id' {rnd.get('patch_id')!r} is not the patch ID of base..head ({actual or 'empty diff'})")
        scope = rnd.get("scope")
        if not isinstance(scope, list) or not scope or not all(isinstance(p, str) and p for p in scope):
            add("L1", f"round {index}: 'scope' must list the files read; zero findings count only with files read")
            rnd["scope"] = []
        findings = rnd.get("findings")
        if not isinstance(findings, list):
            add("L1", f"round {index}: 'findings' must be a list (empty when nothing was found)")
            rnd["findings"] = findings = []
        seen = set()
        for finding in findings:
            if not isinstance(finding, dict):
                add("L2", f"round {index}: a finding is not an object")
                continue
            fid = finding.get("id")
            # A fixed finding's quote is gone at this head: prove it where the ID was raised.
            raised = first[fid][1] if fid in first and finding.get("status") == "fixed" else None
            check_finding(repo, rnd, finding, add, proof=raised)
            if finding.get("status") == "fixed" and fid in last_open \
                    and last_open[fid].get("patch_id") == rnd.get("patch_id"):
                add("L9", f"round {index} finding {fid}: fixed on the same patch where it was open "
                          f"(round {last_open[fid]['round']}); a fix needs a new patch")
            if finding.get("status") == "open" and fid:
                last_open[fid] = rnd
            if fid and fid in seen:
                add("L6", f"round {index} finding {fid}: the ID appears twice in one round")
            seen.add(fid)
            if fid in first:
                changed = [k for k in STABLE if finding.get(k) != first[fid][0].get(k)]
                if changed:
                    add("L6", f"round {index} finding {fid}: {', '.join(changed)} changed since an earlier round; a changed finding gets a new ID")
            elif fid:
                first[fid] = (finding, rnd)
    failed = 0
    for index, rnd in enumerate(rounds, 1):
        disposition = rnd.get("disposition")
        if disposition is not None and disposition not in DISPOSITIONS:
            add("L8", f"round {index}: disposition {disposition!r} is not one of {', '.join(DISPOSITIONS)}")
        failing = bool(blocking(latest(rounds, index)))
        failed += failing
        if disposition is not None and not (failing and failed > cap):
            add("L8", f"round {index}: a disposition belongs only on a failed round past the cap of {cap}; remove it")
        if failing:
            if failed > cap and disposition not in DISPOSITIONS:
                add("L8", f"round {index}: failed round {failed} is past the cap of {cap}; record the disposition (fixed, replanned or filed) the calling contract's disposition policy gave, or the owner's decision without a contract")
    return problems


def load(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return json.load(handle), None
    except (OSError, json.JSONDecodeError) as error:
        return None, f"L1: cannot read {path}: {error}"


def verdict(args):
    base, head = commit(args.repo, args.base), commit(args.repo, args.head)
    if not base or not head:
        print(f"git failed: cannot resolve --base {args.base} or --head {args.head} in {args.repo}: not run")
        return 1
    candidate = patch_id(args.repo, base, head)
    if candidate is None:
        print(f"git failed: git diff or git patch-id did not run in {args.repo}: not run")
        return 1
    if not candidate:
        print(f"no change between {args.base} and {args.head}: nothing to review")
        return 1
    print(f"patch-id: {candidate}")
    if not args.ledger:
        print("verdict: not reviewed: no ledger given")
        return 1
    ledger, error = load(args.ledger)
    problems = [error] if error else check(ledger, args.repo)
    if problems:
        print("\n".join(problems))
        print("verdict: ledger invalid")
        return 1
    last = ledger["rounds"][-1]
    print(f"ledger patch-id: {last['patch_id']} (round {last['round']})")
    if last["patch_id"] != candidate:
        print("verdict: stale: the ledger reviewed another patch; review this one again")
        return 1
    state = latest(ledger["rounds"], len(ledger["rounds"]))
    files = len(last["scope"])
    scope = f"{files} file{'s' if files != 1 else ''} read"
    open_ = blocking(state)
    for f in open_:
        print(f"open {f['severity']} {f['id']} ({f['origin']}, {f['lens']}) at {f['location']}: {f['problem']}")
    if last.get("disposition"):
        print(f"disposition: {last['disposition']} (round {last['round']})")
    if open_:
        print(f"verdict: changes needed ({scope})")
        return 1
    nits = sum(1 for f in state.values() if f.get("status") == "open")
    print(f"verdict: pass: no open Blocker or Major; {nits} open Nit{'s' if nits != 1 else ''}; {scope}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("check", help="check a ledger against rules L1 to L9")
    one.add_argument("ledger")
    one.add_argument("--repo", default=".")
    two = sub.add_parser("verdict", help="patch ID and verdict for base..head")
    two.add_argument("--base", required=True)
    two.add_argument("--head", required=True)
    two.add_argument("--ledger")
    two.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    if args.command == "verdict":
        return verdict(args)
    ledger, error = load(args.ledger)
    problems = [error] if error else check(ledger, args.repo)
    print("\n".join(problems) or "pass")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
