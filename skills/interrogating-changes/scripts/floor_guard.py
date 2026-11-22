#!/usr/bin/env python3
"""Flag a unified diff that makes a check easier to pass (a lowered bar).

  git diff <base>..<head> | python3 floor_guard.py [--accept <id>=<reason> ...]
  python3 floor_guard.py change.diff [--accept <id>=<reason> ...]

It flags, per file in the diff:
  assert-  an assertion removed with no added assertion to replace it
  skip-    an added skip, ignore or focus marker (pytest.mark.skip, it.skip, it.only, t.Skip, ...)
  silence- an added or widened checker silencer (noqa, eslint-disable, @ts-ignore, type: ignore,
           nosec, nolint, ...): '# noqa: F401' to '# noqa' is widened
  floor-   a lowered, removed or commented-out number on a coverage, threshold, min, minimum, fail_under,
           lines, branches, functions or statements key
  ci-      an added continue-on-error: true or allow_failure: true, or || true in a CI file

Each flag prints as "<id>: <path>:<line>: <what>". Exits 0 and prints "pass" when there is no
flag, or when every flag is accepted with --accept <id>=<reason>; accepted flags print as
"accepted <id>: <reason>". Otherwise exits 1. Input with no "+++" file header prints
"no diff on input: not run" (or "no text changes in the diff: not run" for a rename-only or
binary-only diff) and exits 1. Standard library only. It reads text patterns,
not a language's syntax, so a pass means no pattern matched, not that the tests are as strong.
"""

import argparse
import hashlib
import re
import sys
from collections import Counter

ASSERTION = re.compile(
    r"^\s*(?:await\s+|with\s+)?(?:assert\b|(?:self\.|this\.|t\.|s\.)?assert\w*!?\s*\(|expect\s*\("
    r"|pytest\.raises\s*\(|require\.\w+\s*\(|t\.(?:Error|Fatal)f?\s*\()|\.should\b")
SKIP = re.compile(
    r"@pytest\.mark\.(?:skip|skipif|xfail)\b|\bunittest\.skip\w*|\.skipTest\s*\(|\bpytest\.(?:skip|xfail)\s*\("
    r"|\b(?:it|test|describe|context)\.(?:skip|only|todo)\b|\b(?:xit|xtest|xdescribe)\s*\("
    r"|\bt\.Skip\w*\s*\(|#\[ignore\]|@(?:Disabled|Ignore)\b")
SILENCER = re.compile(
    r"\bnoqa\b|eslint-disable(?:-next-line|-line)?|@ts-(?:ignore|nocheck|expect-error)\b|\btype:\s*ignore\b|\bnosec\b"
    r"|\bnolint\b|pylint:\s*disable", re.I)
CI_IGNORE = re.compile(r"\b(?:continue-on-error|allow_failure)\s*:\s*true\b")
OR_TRUE = re.compile(r"\|\|\s*(?:true|:)(?![\w-])")
CI_PATHS = re.compile(
    r"(?:^|/)(?:\.github/(?:workflows|actions)/|\.gitlab-ci\.ya?ml$|\.gitlab/|\.circleci/|azure-pipelines[^/]*\.ya?ml$"
    r"|\.azure-pipelines/|Jenkinsfile$|\.buildkite/|bitbucket-pipelines\.ya?ml$|\.travis\.ya?ml$)")
COMMENT = re.compile(r"^\s*(?:#|//|;|/\*)")
BAR_WORDS = {"coverage", "threshold", "min", "minimum", "lines", "branches", "functions", "statements"}
NUMBER = r"(?P<num>-?\d+(?:\.\d+)?)"
KEY_VALUE = re.compile(r"""(?P<key>[A-Za-z_][\w.\-]*)["']?\s*(?::=|[:=])\s*["']?""" + NUMBER)
FLAG_VALUE = re.compile(r"--(?P<key>[\w\-]+)\s+" + NUMBER)


def parse(text):
    """Yield (path, hunk) for each hunk; a hunk is a list of (sign, old_line, new_line, text)."""
    path, old_path, lines = None, None, iter(text.splitlines())
    for line in lines:
        if line.startswith("--- "):
            old_path = line[4:].split("\t")[0]
            old_path = old_path[2:] if old_path.startswith("a/") else old_path
        elif line.startswith("+++ "):
            path = line[4:].split("\t")[0]
            path = path[2:] if path.startswith("b/") else path
            if path == "/dev/null":
                path = old_path
        elif line.startswith("@@") and path:
            match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if not match:
                continue
            old, old_left = int(match[1]), int(match[2] or 1)
            new, new_left = int(match[3]), int(match[4] or 1)
            hunk = []
            while old_left > 0 or new_left > 0:
                body = next(lines, None)
                if body is None:
                    break
                sign, rest = (body[:1] or " "), body[1:]
                if sign == "\\":
                    continue
                if sign == "-":
                    hunk.append(("-", old, None, rest))
                    old, old_left = old + 1, old_left - 1
                elif sign == "+":
                    hunk.append(("+", None, new, rest))
                    new, new_left = new + 1, new_left - 1
                else:
                    old, new, old_left, new_left = old + 1, new + 1, old_left - 1, new_left - 1
            yield path, hunk


def bar_key(key):
    lowered = key.lower().replace("-", "_")
    words = re.split(r"[_.\s]+", re.sub(r"([a-z])([A-Z])", r"\1_\2", key).lower())
    return "fail_under" in lowered or bool(BAR_WORDS & set(words))


def bars(text):
    """[(key, number)] for each bar key with a number on the line."""
    found = []
    for pattern in (KEY_VALUE, FLAG_VALUE):
        for match in pattern.finditer(text):
            if bar_key(match["key"]):
                found.append((match["key"], float(match["num"])))
    return found


def silencers(text):
    """[(family, codes)] for each silencer on the line: '# noqa: F401' gives ('noqa', {'F401'}).

    No codes means the silencer covers every rule. @ts- markers take no codes.
    """
    found = []
    for match in SILENCER.finditer(text):
        family = re.sub(r"\s+", "", match.group(0)).lower()
        rest = re.split(r"\*/|#|//|--", text[match.end():], maxsplit=1)[0]
        codes = set() if family.startswith("@ts-") else set(re.findall(r"[\w@/.-]+", rest))
        found.append((family, frozenset(codes)))
    return found


def markers(pattern, text):
    return [m.group(0).replace(" ", "") for m in pattern.finditer(text)]


def scan(text):
    """[(prefix, path, line, what)] for every lowered bar in the diff."""
    flags = []
    files = {}
    for path, hunk in parse(text):
        files.setdefault(path, []).append(hunk)
    for path, hunks in files.items():
        rows = [row for hunk in hunks for row in hunk]
        removed = [r for r in rows if r[0] == "-"]
        added = [r for r in rows if r[0] == "+"]
        # Assertions: a removed assertion needs an added one in the same file.
        gone = [r for r in removed if ASSERTION.search(r[3])]
        spare = len([r for r in added if ASSERTION.search(r[3])])
        for row in gone[spare:] if len(gone) > spare else []:
            flags.append(("assert", path, row[1], f"assertion removed with no replacement: {row[3].strip()}"))
        # Markers: an added marker counts only when the file did not lose the same marker.
        checks = [("skip", SKIP, "skip marker added"), ("ci", CI_IGNORE, "CI failure ignored")]
        if CI_PATHS.search(path):
            checks.append(("ci", OR_TRUE, "CI failure ignored"))
        for prefix, pattern, what in checks:
            kept = Counter(m for r in removed for m in markers(pattern, r[3]))
            for row in added:
                for marker in markers(pattern, row[3]):
                    if kept[marker]:
                        kept[marker] -= 1
                    else:
                        flags.append((prefix, path, row[2], f"{what}: {row[3].strip()}"))
        # Silencers: an added one must be covered by a removed one at least as wide.
        old = [s for r in removed for s in silencers(r[3])]
        for row in added:
            for family, codes in silencers(row[3]):
                cover = next((s for s in old if s[0] == family and (not s[1] or (codes and codes <= s[1]))), None)
                if cover:
                    old.remove(cover)
                else:
                    flags.append(("silence", path, row[2], f"checker silencer added or widened: {row[3].strip()}"))
        # Numbers: pair each removed bar with the next added bar of the same key in the hunk.
        # A commented-out line holds no bar, so commenting one out removes it.
        for hunk in hunks:
            new_values = {}
            for row in hunk:
                if row[0] == "+" and not COMMENT.match(row[3]):
                    for key, value in bars(row[3]):
                        new_values.setdefault(key, []).append((value, row[2]))
            for row in hunk:
                if row[0] != "-" or COMMENT.match(row[3]):
                    continue
                for key, value in bars(row[3]):
                    if new_values.get(key):
                        new, line = new_values[key].pop(0)
                        if new < value:
                            flags.append(("floor", path, line, f"{key} lowered from {value:g} to {new:g}"))
                    else:
                        flags.append(("floor", path, row[1], f"{key} {value:g} removed or commented out, with no new value"))
    return flags


def identify(flags):
    """Give each flag a stable '<prefix>-<6 hex>' ID from its kind, path and text."""
    out, used = [], Counter()
    for prefix, path, line, what in flags:
        digest = hashlib.sha1(f"{prefix}\0{path}\0{what}".encode()).hexdigest()
        used[digest] += 1
        if used[digest] > 1:
            digest = hashlib.sha1(f"{digest}\0{used[digest]}".encode()).hexdigest()
        out.append((f"{prefix}-{digest[:6]}", path, line, what))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("diff", nargs="?", help="unified diff file (default: standard input)")
    parser.add_argument("--accept", action="append", default=[], metavar="ID=REASON",
                        help="accept one flag, with the reason printed in the output")
    args = parser.parse_args(argv)
    if args.diff:
        with open(args.diff, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    if not re.search(r"^\+\+\+ ", text, re.M):
        has_diff = re.search(r"^diff --git ", text, re.M)
        print("no text changes in the diff: not run" if has_diff else "no diff on input: not run")
        return 1
    flags = identify(scan(text))
    known = {flag[0] for flag in flags}
    accepted, problems = {}, []
    for item in args.accept:
        flag_id, _, reason = item.partition("=")
        if not reason.strip():
            problems.append(f"--accept {flag_id}: give a reason after '='")
        elif flag_id not in known:
            problems.append(f"--accept {flag_id}: no such flag in this diff")
        else:
            accepted[flag_id] = reason.strip()
    for flag_id, path, line, what in flags:
        if flag_id in accepted:
            print(f"accepted {flag_id}: {accepted[flag_id]} ({path}:{line}: {what})")
        else:
            problems.append(f"{flag_id}: {path}:{line}: {what}")
    print("\n".join(problems) or "pass")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
