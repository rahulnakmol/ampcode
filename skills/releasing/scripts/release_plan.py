#!/usr/bin/env python3
"""Plan a branch promotion and decide GO or NO-GO. It reads git and never changes a ref.

  python3 release_plan.py plan --repo PATH --from dev --to rolling --kind rolling \\
      [--date YYYY-MM-DD] [--label TEXT [--slug TEXT]]
  python3 release_plan.py plan --repo PATH --from rolling --to main --kind stable --version X.Y.Z
  python3 release_plan.py go <the same plan options> --plan-digest HEX --rollback FILE \\
      [--check NAME=pass|fail ...]

plan prints the commits to promote, the merge message, the tag, the release notes, the checks,
the rollback point, the commands to run after approval and a "Plan digest:" line, and exits 0.
When the target already contains the source it prints "nothing to promote" and exits 0. When a
rule is broken it prints one line per rule and exits 1.

go computes the plan again, compares its digest with --plan-digest, reads the rollback plan and
the reported checks, and prints GO (exit 0) or NO-GO with one reason per line (exit 1).

A branch name resolves to <remote>/<name> when that remote-tracking branch exists, otherwise to
the local branch. Run `git fetch` first. Per-repository settings live in .agents/releasing.json
(or --config): see ../reference/promotion.md. Standard library only.
"""

import argparse
import datetime
import hashlib
import json
import re
import shlex
import string
import subprocess
import sys
from pathlib import Path

DEFAULTS = {
    "remote": "origin",
    "rolling_message": "Rolling snapshot",
    "rolling_tag": "rolling",
    "stable_message": "Release",
    "stable_tag": "v",
    "checks": {
        "rolling": {
            "full-suite": "the full rolling suite is green on {from} at {source}",
            "source-ci": "CI is green on {from} at {source}",
        },
        "stable": {
            "full-suite": "the full rolling suite is green on {from} at {source}",
            "source-ci": "CI is green on {from} at {source}",
            "release-decision": "the owner's explicit stable-release decision for {tag} is recorded",
        },
    },
}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
HEX = re.compile(r"\b[0-9a-f]{7,40}\b")
FIELDS = ("from", "to", "source", "tag")


class Refused(Exception):
    """The plan cannot be made; args holds one line per broken rule."""


def git(repo, *args):
    run = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return run.returncode, run.stdout.strip()


def sha_of(repo, ref):
    code, out = git(repo, "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}")
    return out if code == 0 and out else None


def is_ancestor(repo, commit, of):
    return git(repo, "merge-base", "--is-ancestor", commit, of)[0] == 0


def load_config(repo, path):
    config = json.loads(json.dumps(DEFAULTS))
    file = Path(path) if path else Path(repo) / ".agents" / "releasing.json"
    if not file.is_file():
        if path:
            raise Refused(f"config {path} not found")
        return config
    try:
        given = json.loads(file.read_text())
    except (OSError, ValueError) as error:
        raise Refused(f"config {file} is not valid JSON: {error}")
    if not isinstance(given, dict):
        raise Refused(f"config {file} must hold a JSON object")
    problems = [f"config {file}: unknown key {key!r}" for key in sorted(set(given) - set(DEFAULTS))]
    for key in sorted(set(given) & set(DEFAULTS) - {"checks"}):
        value = given[key]
        if not isinstance(value, str) or not value.strip() or "\n" in value:
            problems.append(f"config {file}: {key} must be a non-empty one-line string, got {value!r}")
        else:
            config[key] = value
    checks = given.get("checks", {})
    if not isinstance(checks, dict):
        problems.append(f"config {file}: checks must be an object of kinds, got {checks!r}")
        checks = {}
    for kind, table in checks.items():
        where = f"config {file}: checks.{kind}"
        if kind not in DEFAULTS["checks"]:
            problems.append(f"{where} is not a kind; use rolling or stable")
        elif not isinstance(table, dict) or not table:
            problems.append(f"{where} must be a non-empty object of name: description, got {table!r}")
        else:
            for name, text in table.items():
                if not SLUG.fullmatch(name):
                    problems.append(f"{where}: check name {name!r} must be lowercase words joined by hyphens")
                elif not isinstance(text, str) or not text.strip():
                    problems.append(f"{where}.{name} must be a non-empty string")
                else:
                    problems += [f"{where}.{name}: {p}" for p in placeholder_problems(text)]
            config["checks"][kind] = table
    if problems:
        raise Refused(*problems)
    return config


def placeholder_problems(text):
    """Problems with the {placeholders} in a check description."""
    try:
        names = [field for _, field, _, _ in string.Formatter().parse(text) if field is not None]
    except ValueError as error:
        return [f"bad braces in {text!r}: {error}"]
    return [f"unknown placeholder {{{n}}}; use {', '.join('{' + f + '}' for f in FIELDS)}"
            for n in names if n not in FIELDS]


def tag_problem(repo, tag):
    if git(repo, "check-ref-format", f"refs/tags/{tag}")[0] != 0:
        return f"{tag!r} is not a valid tag name (git check-ref-format)"
    return None


def resolve(repo, name, remote):
    """(display name, sha, from_remote) for a branch; prefers the remote-tracking branch."""
    remote_sha = sha_of(repo, f"refs/remotes/{remote}/{name}")
    local_sha = sha_of(repo, f"refs/heads/{name}")
    if remote_sha:
        note = None
        if local_sha and local_sha != remote_sha:
            note = f"note: local {name} differs from {remote}/{name}; the plan uses {remote}/{name}"
        return f"{remote}/{name}", remote_sha, True, note
    if local_sha:
        return name, local_sha, False, None
    raise Refused(f"branch {name} not found as {remote}/{name} or as a local branch")


def tags(repo):
    return set(git(repo, "tag", "--list")[1].split())


def last_tag(repo, pattern, target):
    code, out = git(repo, "describe", "--tags", "--abbrev=0", "--match", pattern, target)
    return out if code == 0 else "none"


def missing_from_source(repo, source, target):
    """Target commits the source lacks, minus earlier promotion merges and cherry-picks."""
    out = git(repo, "rev-list", "--right-only", "--cherry-pick", f"{source}...{target}")[1]
    missing = []
    for commit in out.split():
        parents = git(repo, "rev-list", "--parents", "-n", "1", commit)[1].split()[1:]
        subject = git(repo, "log", "-1", "--format=%s", commit)[1]
        if len(parents) > 1 and all(brought_into(repo, parents[0], p, source) for p in parents[1:]):
            # An earlier promotion or rollback merge: its commits are in the source. It may still
            # carry changes of its own (an evil merge).
            extra = own_changes(repo, commit, parents)
            if extra:
                missing.append(f"{commit[:7]} {subject} (changes of its own, not from a clean merge of "
                               f"its parents: {', '.join(extra)})")
            continue
        if len(parents) < 2:
            # A cherry-pick or revert whose twin on the source a later promotion already brought
            # into the target: --cherry-pick above no longer sees that twin. Look for it among the
            # source commits the target did not hold when this commit was made.
            own = patch_ids(repo, "-1", commit)
            if own and own <= patch_ids(repo, source, *[f"^{p}" for p in parents]):
                continue
        missing.append(f"{commit[:7]} {subject}")
    return missing


def patch_ids(repo, *revs):
    """The stable patch IDs of the non-merge commits that `git log <revs>` lists."""
    log = subprocess.run(["git", "-C", str(repo), "log", "--no-merges", "-p", "--format=commit %H", *revs],
                         capture_output=True)
    ids = subprocess.run(["git", "-C", str(repo), "patch-id", "--stable"], input=log.stdout, capture_output=True)
    return {line.split()[0] for line in ids.stdout.decode(errors="replace").splitlines() if line.strip()}


def own_changes(repo, merge, parents):
    """Paths where a merge's tree differs from `git merge-tree` of its two parents. Where the
    parents conflict, taking the second parent's version (the merged-in side) is no change."""
    if len(parents) != 2:
        return [f"{len(parents)} parents, not checked"]
    code, out = git(repo, "merge-tree", "--write-tree", "--name-only", "--no-messages", "-z", *parents)
    if code not in (0, 1):
        return ["git merge-tree failed (git 2.38 or later is needed), not checked"]
    tree, *conflicted = [p for p in out.split("\0") if p]
    changed = [p for p in git(repo, "diff", "--name-only", "--no-renames", "-z", tree, merge)[1].split("\0") if p]
    return [p for p in changed
            if p not in conflicted or sha_of_path(repo, merge, p) != sha_of_path(repo, parents[1], p)]


def sha_of_path(repo, commit, path):
    code, out = git(repo, "rev-parse", "--verify", "--quiet", f"{commit}:{path}")
    return out if code == 0 else None


def brought_into(repo, first, other, source):
    """True when every commit a merge brought from `other` is in the source, or is a
    non-merge commit with the same patch as a source commit (cherry-equivalent)."""
    if is_ancestor(repo, other, source):
        return True
    brought = set(git(repo, "rev-list", f"{first}..{other}")[1].split())
    if not brought:
        return True
    unmatched = set(git(repo, "rev-list", "--left-only", "--cherry-pick", f"{other}...{source}")[1].split())
    return not (brought & unmatched)


def build(args):
    """Return the plan as a dict, or None when there is nothing to promote."""
    repo = Path(args.repo).resolve()
    if git(repo, "rev-parse", "--git-dir")[0] != 0:
        raise Refused(f"{repo} is not a git repository")
    config = load_config(repo, args.config)
    remote = config["remote"]
    if args.source == args.target:
        raise Refused("--from and --to must name different branches")
    source_name, source, _, source_note = resolve(repo, args.source, remote)
    target_name, target, target_remote, target_note = resolve(repo, args.target, remote)
    if is_ancestor(repo, source, target):
        return {"nothing": f"nothing to promote: {args.target} ({target_name}) already contains "
                           f"{args.source} ({source_name}) at {source[:7]}"}

    problems = []
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all")[1].splitlines()
    if dirty:
        paths = ", ".join(line.split(None, 1)[1] for line in dirty[:5]) + (", ..." if len(dirty) > 5 else "")
        problems.append(f"the working tree of {repo} is not clean ({paths}): commit or stash "
                        "changes, and keep the rollback plan, decision brief and release summary outside the checkout")
    for line in missing_from_source(repo, source, target):
        problems.append(f"{args.target} has a commit missing from {args.source}: {line} "
                        f"(bring it into {args.source} first, or explain it)")
    existing = tags(repo)
    tag = message = None

    if args.kind == "rolling":
        if args.version:
            problems.append("--version is for --kind stable")
        if args.slug and not args.label:
            problems.append("--slug needs --label")
        date = args.date or datetime.date.today().isoformat()
        try:
            if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                raise ValueError
            datetime.date.fromisoformat(date)
        except ValueError:
            problems.append(f"--date must be YYYY-MM-DD, got {date!r}")
            date = None
        slug = None
        if args.label:
            slug = args.slug or re.sub(r"[^a-z0-9]+", "-", args.label.lower()).strip("-")
            if not SLUG.fullmatch(slug):
                problems.append(f"--slug must be lowercase words joined by hyphens, got {slug!r}")
        if date:
            base = f"{config['rolling_tag']}-{date}"
            message = f"{config['rolling_message']}: {date}"
            tag = base
            if args.label:
                message += f" {args.label.strip()}"
                tag = f"{base}-{slug}"
                if tag in existing:
                    problems.append(f"tag {tag} already exists: choose another --label or --slug")
            else:
                same_day = sorted(t for t in existing if t == base or t.startswith(base + "-"))
                if same_day:
                    problems.append(f"tag {same_day[0]} already exists: a second snapshot on "
                                    f"{date} needs --label")
        tag_type = "lightweight"
        last = ("Last snapshot", last_tag(repo, f"{config['rolling_tag']}-*", target))
    else:
        for flag, value in (("--label", args.label), ("--slug", args.slug), ("--date", args.date)):
            if value:
                problems.append(f"{flag} is for --kind rolling")
        prefix = config["stable_tag"]
        match = VERSION.fullmatch(args.version or "")
        if not match:
            problems.append(f"--kind stable needs --version x.y.z, got {args.version!r}")
        else:
            version = tuple(int(n) for n in match.groups())
            tag = prefix + ".".join(map(str, version))
            message = f"{config['stable_message']}: {tag}"
            releases = [(tuple(int(n) for n in m.groups()), t) for t in existing
                        if t.startswith(prefix) and (m := VERSION.fullmatch(t[len(prefix):]))
                        and not t[len(prefix):].startswith("v")]
            if releases:
                highest, highest_tag = max(releases)
                if version <= highest:
                    problems.append(f"{tag} is not greater than the last release {highest_tag}")
            if tag in existing:
                problems.append(f"tag {tag} already exists")
        tag_type = "annotated"
        last = ("Last release", last_tag(repo, f"{prefix}[0-9]*", target))
    if tag and (bad := tag_problem(repo, tag)):
        problems.append(bad)

    if problems:
        raise Refused(*problems)

    log = git(repo, "log", "--left-only", "--cherry-mark", "--no-merges", "--format=%m %H %s",
              f"{source}...{target}")[1]
    commits = []
    for line in log.splitlines():
        mark, sha, subject = (line.split(" ", 2) + [""])[:3]
        commits.append({"sha": sha, "subject": subject, "picked": mark == "="})
    fields = {"from": args.source, "source": source[:7], "to": args.target, "tag": tag}
    checks = {name: text.format_map(fields) for name, text in config["checks"][args.kind].items()}

    q = shlex.quote
    # Work on the planned target commit, so the push fails if the remote branch moved meanwhile.
    commands = [f"git switch --detach {target}" if target_remote else f"git switch {q(args.target)}",
                f"git merge --no-ff -m {q(message)} {source}",
                f"git tag -a {q(tag)} -F ../release-summary.md" if tag_type == "annotated"
                else f"git tag {q(tag)}"]
    if target_remote:
        commands.append(f"git push --atomic {q(remote)} {q('HEAD:refs/heads/' + args.target)} "
                        f"{q('refs/tags/' + tag)}")

    plan = {
        "kind": args.kind, "from": args.source, "from_ref": source_name, "source": source,
        "to": args.target, "to_ref": target_name, "target": target, "message": message,
        "tag": tag, "tag_type": tag_type, "commits": commits, "checks": checks,
        "commands": commands,
    }
    plan["digest"] = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
    plan["last"] = last
    plan["notes"] = [n for n in (source_note, target_note) if n]
    plan["repo"] = str(repo)
    return plan


def render(plan, args):
    title = "rolling snapshot" if plan["kind"] == "rolling" else "stable release"
    out = [f"Plan: {title} from {plan['from']} to {plan['to']}", *plan["notes"],
           f"Repository: {plan['repo']}",
           f"From: {plan['from']} ({plan['from_ref']}) at {plan['source']}",
           f"To: {plan['to']} ({plan['to_ref']}) at {plan['target']}",
           f"{plan['last'][0]}: {plan['last'][1]}",
           f"Merge: non-fast-forward (git merge --no-ff), one merge commit on {plan['to']}",
           f"Merge message: \"{plan['message']}\"",
           f"Tag: {plan['tag']} ({plan['tag_type']}) on the merge commit",
           f"Commits to promote ({len(plan['commits'])}):"]
    for c in plan["commits"]:
        picked = f" (already on {plan['to']} by cherry-pick)" if c["picked"] else ""
        out.append(f"  {c['sha'][:7]} {c['subject']}{picked}")
    out.append(f"Release notes (since {plan['last'][1]}):")
    out += [f"- {c['subject']}" for c in plan["commits"]]
    out.append("Checks before GO:")
    out += [f"- {name}: {text}" for name, text in plan["checks"].items()]
    out.append(f"Rollback point: {plan['to']} at {plan['target']}")
    out.append("Commands after approval (outside effects; this script runs none of them):")
    out += [f"  {c}" for c in plan["commands"]]
    out.append(f"Plan digest: {plan['digest']}")
    options = plan_options(args)
    checks = " ".join(f"--check {name}=<pass|fail>" for name in plan["checks"])
    out.append(f"Next: python3 <skill>/scripts/release_plan.py go {options} --plan-digest {plan['digest']} "
               f"--rollback ../rollback.md {checks}")
    return "\n".join(out)


def plan_options(args):
    parts = ["--repo", args.repo, "--from", args.source, "--to", args.target, "--kind", args.kind]
    if args.kind == "rolling":
        parts += ["--date", args.date or datetime.date.today().isoformat()]
    for flag, value in (("--label", args.label), ("--slug", args.slug), ("--version", args.version),
                        ("--config", args.config)):
        if value:
            parts += [flag, value]
    return " ".join(shlex.quote(p) for p in parts)


def decide(plan, args):
    """Reasons for NO-GO; empty means GO."""
    reasons = []
    given = args.plan_digest.strip().lower().removeprefix("sha256:")
    if given != plan["digest"]:
        reasons.append(f"plan digest {given[:12]}… does not match the current plan "
                       f"{plan['digest'][:12]}…: plan again and get the new plan approved")
    rollback = Path(args.rollback)
    if not rollback.is_file():
        reasons.append(f"rollback plan {rollback} not found: write it before GO")
    else:
        text = rollback.read_text(errors="replace")
        if not text.strip():
            reasons.append(f"rollback plan {rollback} is empty")
        elif not any(plan["target"].startswith(h) for h in HEX.findall(text.lower())):
            reasons.append(f"rollback plan {rollback} does not name the rollback point: "
                           f"{plan['to']} at {plan['target'][:7]}")
    results = {}
    for item in args.check:
        name, sep, value = item.partition("=")
        if not sep or not name or value not in ("pass", "fail"):
            reasons.append(f"check {item!r} must be NAME=pass or NAME=fail")
            continue
        results[name] = "fail" if results.get(name) == "fail" else value
    for name in plan["checks"]:
        if name not in results:
            reasons.append(f"check {name} not reported: {plan['checks'][name]}")
    reasons += [f"check {name} failed" for name, value in results.items() if value == "fail"]
    return reasons


def main(argv=None):
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--repo", required=True, help="path to the git repository")
    shared.add_argument("--from", dest="source", required=True, help="branch to promote from")
    shared.add_argument("--to", dest="target", required=True, help="branch to promote to")
    shared.add_argument("--kind", required=True, choices=("rolling", "stable"))
    shared.add_argument("--version", help="stable only: x.y.z, greater than the last release")
    shared.add_argument("--label", help="rolling only: text after the date in the message")
    shared.add_argument("--slug", help="rolling only: tag suffix; default: the label in lowercase with hyphens")
    shared.add_argument("--date", help="rolling only: YYYY-MM-DD; default: today")
    shared.add_argument("--config", help="settings file; default: <repo>/.agents/releasing.json if present")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", parents=[shared], help="print the promotion plan and its digest")
    go = commands.add_parser("go", parents=[shared], help="print GO or NO-GO for an approved plan digest")
    go.add_argument("--plan-digest", required=True, help="the digest the plan printed")
    go.add_argument("--rollback", required=True, help="file holding the rollback plan")
    go.add_argument("--check", action="append", default=[], help="NAME=pass or NAME=fail; repeat")
    args = parser.parse_args(argv)

    try:
        plan = build(args)
    except Refused as refused:
        if args.command == "go":
            print("NO-GO")
            print("\n".join(f"- {line}" for line in refused.args))
        else:
            print("\n".join(refused.args))
        return 1
    if "nothing" in plan:
        if args.command == "go":
            print(f"NO-GO\n- {plan['nothing']}")
            return 1
        print(plan["nothing"])
        return 0
    if args.command == "plan":
        print(render(plan, args))
        return 0
    reasons = decide(plan, args)
    if reasons:
        print("NO-GO")
        print("\n".join(f"- {r}" for r in reasons))
        return 1
    print("GO")
    print(f"- plan digest {plan['digest']}")
    print(f"- {plan['to']} gets one merge of {plan['from']} at {plan['source'][:7]} "
          f"and the tag {plan['tag']}")
    print("- run it only when the mission contract pre-authorizes this exact effect, "
          "or the owner approves this plan digest")
    return 0


if __name__ == "__main__":
    sys.exit(main())
