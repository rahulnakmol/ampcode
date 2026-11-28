#!/usr/bin/env python3
"""Flag a unified diff that makes a check easier to pass (a lowered bar).

  git diff <base>...<head> | python3 floor_guard.py [--accept <id>=<reason> ...]
  python3 floor_guard.py change.diff [--accept <id>=<reason> ...]

It flags, per file in the diff:
  assert-  an assertion removed with no added assertion to replace it (a commented-out line, with
           #, //, ;, /*, <!-- or --, is no assertion); also XCTAssert..., pgTAP, tSQLt, HUnit, hspec
  skip-    an added skip, ignore or focus marker (pytest.mark.skip, pytestmark, @skip(, it.skip,
           test.skipIf, test.if, describe.if, it.runIf, test.failing, test.concurrent.skip, it.only,
           fit, fdescribe, { skip: true }, t.Skip, XCTSkip, XCTSkipIf, Rust #[ignore], xUnit
           [Fact(Skip = ...)], NUnit [Ignore] and [Explicit], Assert.Ignore, Skip.If, ...)
  silence- an added or widened checker silencer (noqa, eslint-disable, @ts-ignore, type: ignore,
           nosec, nolint, C# #pragma warning disable and [SuppressMessage], Rust #[allow(...)], ...):
           '# noqa: F401' to '# noqa' is widened
  floor-   a lowered, removed or commented-out number on a coverage, threshold, min, minimum, fail_under,
           lines, branches, functions or statements key, also as XML (JaCoCo <minimum>0.80</minimum>)
  ci-      an added continue-on-error: true or allow_failure: true, or || true in a CI file
  retry-   an added or raised retry of failing tests in a test, test or build config, CI file or verify.json
           (retries: 2, --retries 2, --retry=2, reruns = 2, jest.retryTimes(2), this.retries(2),
           pytest.mark.flaky, @flaky, NUnit [Retry(3)], xRetry MaxRetries = 3, nextest retries = 2):
           fix the flaky test's cause, or delete it with a reason
  observe- a package newly set to "mode": "observe" in verify.json (editing a package that already
           observes is not): the pure-core rule stops failing the build
  removed- a package's "name" removed from verify.json: its end-to-end and pure-core checks go
A commented-out line holds no marker.

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
    r"|pytest\.raises\s*\(|require\.\w+\s*\(|t\.(?:Error|Fatal)f?\s*\(|XCTAssert\w*\s*\(|assert[A-Z]\w*\s+[\"(\[\w]"
    r"|(?i:select)\s+(?:ok|is|isnt|matches|cmp_ok|results_eq|set_eq|bag_eq|throws_ok|lives_ok|is_empty)\s*\("
    r"|(?i:exec(?:ute)?)\s+tSQLt\.(?:Assert|Fail)\w*|(?:Assert|CollectionAssert|StringAssert|ClassicAssert)\.\w+\s*[(<])"
    r"|\.should\b|\.Should\(\)|`should\w*`")
SKIP = re.compile(
    r"(?:@|\bpytestmark\s*=\s*\[?\s*)?\bpytest\.mark\.(?:skip|skipif|xfail)\b|\bunittest\.skip\w*|\.skipTest\s*\("
    r"|\bpytest\.(?:skip|xfail)\s*\(|^\s*@skip(?:If|Unless)?\s*\("
    r"|\b(?:it|test|describe|context)(?:\.(?:concurrent|sequential|serial))*"
    r"\.(?:skip(?:If|Unless)?|only|todo(?:If)?|if|runIf|failing)\b"
    r"|\b(?:xit|xtest|xdescribe)\s*\(|(?<![\w.$])(?<!def )(?:fit|fdescribe)\s*\("
    r"|\bt\.Skip\w*\s*\(|#\[ignore\b|@(?:Disabled|Ignore)\b|\[(?:Fact|Theory|SkippableFact)\s*\([^)]*\bSkip\s*="
    r"|\[\s*(?:Ignore|Explicit)\b|\bAssert\.Ignore\s*\(|\bSkip\.(?:If|IfNot|Unless)\s*\(|\bXCTSkip(?:If|Unless)?\s*\(|[{,]\s*skip\s*:\s*true\b")
SILENCER = re.compile(
    r"\bnoqa\b|eslint-disable(?:-next-line|-line)?|@ts-(?:ignore|nocheck|expect-error)\b|\btype:\s*ignore\b|\bnosec\b"
    r"|\bnolint\b|pylint:\s*disable|#pragma\s+warning\s+disable|\bSuppressMessage\b|#!?\[allow\(", re.I)
# A test retry and its count; mark.flaky and @flaky retry without a count.
RETRY = re.compile(
    r"(?:--retries|--retry|--reruns)(?:=|\s+)(?P<n>\d+)|\b(?:retries|retry|reruns)[\"']?\s*[:=]\s*(?P<m>\d+)"
    r"|\b(?:retryTimes|this\.retries)\s*\(\s*(?P<k>\d+)|\[Retry\s*\(\s*(?P<c>\d+)|\bMaxRetries\s*=\s*(?P<x>\d+)"
    r"|\bmark\.flaky\b|@flaky\b")
# Retries count only in tests, test and build configuration, and CI.
RETRY_PATHS = re.compile(
    r"(?:^|/)(?:tests?|spec|__tests__|e2e|[^/]*\.Tests?)/|(?:^|/)test_[^/]*\.py$|_test\.(?:py|go)$|\.(?:test|spec)\.[cm]?[jt]sx?$"
    r"|Tests?\.cs$|(?:^|/)nextest\.toml$"
    r"|(?:^|/)(?:conftest\.py|[^/]*\.config\.[cm]?[jt]s|\.mocharc[^/]*|pytest\.ini|pyproject\.toml|setup\.cfg|tox\.ini"
    r"|package\.json|bunfig\.toml|verify\.json|Makefile|[^/]*\.mk)$")
OBSERVE = re.compile(r"\"mode\"\s*:\s*\"observe\"")
PACKAGE_NAME = re.compile(r"\"name\"\s*:\s*\"([^\"]*)\"")
CI_IGNORE = re.compile(r"\b(?:continue-on-error|allow_failure)\s*:\s*true\b")
OR_TRUE = re.compile(r"\|\|\s*(?:true|:)(?![\w-])")
CI_PATHS = re.compile(
    r"(?:^|/)(?:\.github/(?:workflows|actions)/|\.gitlab-ci\.ya?ml$|\.gitlab/|\.circleci/|azure-pipelines[^/]*\.ya?ml$"
    r"|\.azure-pipelines/|Jenkinsfile$|\.buildkite/|bitbucket-pipelines\.ya?ml$|\.travis\.ya?ml$)")
COMMENT = re.compile(r"^\s*(?:#(?!\[)|//|;|/\*|<!--|--(?=\s|$))")
BAR_WORDS = {"coverage", "threshold", "min", "minimum", "lines", "branches", "functions", "statements"}
NUMBER = r"(?P<num>-?\d+(?:\.\d+)?)"
KEY_VALUE = re.compile(
    r"""(?P<key>[A-Za-z_][\w.\-]*)["']?\s*(?::=|[:=])\s*(?:BigDecimal(?:\.valueOf)?\(\s*)?["']?""" + NUMBER)
FLAG_VALUE = re.compile(r"--(?P<key>[\w\-]+)\s+" + NUMBER)
XML_VALUE = re.compile(r"<(?P<key>[A-Za-z_][\w.\-]*)>\s*" + NUMBER + r"%?\s*</")


def parse(text):
    """Yield (path, hunk) for each hunk; a hunk is a list of (sign, old_line, new_line, text), with
    sign "-", "+" or " " for an unchanged context line."""
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
                    hunk.append((" ", old, new, rest))
                    old, new, old_left, new_left = old + 1, new + 1, old_left - 1, new_left - 1
            yield path, hunk


def bar_key(key):
    lowered = key.lower().replace("-", "_")
    words = re.split(r"[_.\s-]+", re.sub(r"([a-z])([A-Z])", r"\1_\2", key).lower())
    return "fail_under" in lowered or bool(BAR_WORDS & set(words))


def bars(text):
    """[(key, number)] for each bar key with a number on the line."""
    found = []
    for pattern in (KEY_VALUE, FLAG_VALUE, XML_VALUE):
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


def retries(text):
    """[(setting, count)] for each retry on a line: '--retries 2' gives ('--retries', 2), and
    mark.flaky or @flaky without a count gives a count of 1."""
    found = []
    for m in RETRY.finditer(text):
        group = next((g for g in ("n", "m", "k", "c", "x") if m[g]), None)
        count = m[group] if group else None
        setting = re.sub(r"[\s\"'=:(\[]", "", m.group(0)[:m.start(group) - m.start()] if group else m.group(0))
        found.append((setting, int(count or 1)))
    return found


def changed_pairs(hunks):
    """[(removed row or None, added row)] for each added row: within a run of removed then added
    lines with no unchanged line between them, the i-th added line replaces the i-th removed line."""
    pairs = []
    for hunk in hunks:
        gone, came = [], []
        for row in hunk + [(" ", None, None, "")]:
            if row[0] == "-" and not came:
                gone.append(row)
            elif row[0] == "+":
                came.append(row)
            else:
                pairs += [(gone[i] if i < len(gone) else None, r) for i, r in enumerate(came)]
                gone, came = ([row] if row[0] == "-" else []), []
    return pairs


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
        # Assertions: a removed assertion needs an added one in the same file. A commented-out line
        # holds no assertion.
        gone = [r for r in removed if ASSERTION.search(r[3]) and not COMMENT.match(r[3])]
        spare = len([r for r in added if ASSERTION.search(r[3]) and not COMMENT.match(r[3])])
        for row in gone[spare:] if len(gone) > spare else []:
            flags.append(("assert", path, row[1], f"assertion removed with no replacement: {row[3].strip()}"))
        # Markers: an added marker counts only when the file did not lose the same marker. A
        # commented-out line holds no marker.
        removed_code = [r for r in removed if not COMMENT.match(r[3])]
        added_code = [r for r in added if not COMMENT.match(r[3])]
        checks = [("skip", SKIP, "skip marker added"), ("ci", CI_IGNORE, "CI failure ignored")]
        if CI_PATHS.search(path):
            checks.append(("ci", OR_TRUE, "CI failure ignored"))
        if RETRY_PATHS.search(path) or CI_PATHS.search(path):
            # Each retry setting counts unless the file lost the same setting at least as high.
            old = [r for row in removed_code for r in retries(row[3])]
            for row in added_code:
                for setting, count in retries(row[3]):
                    cover = max((o for o in old if o[0] == setting and o[1] >= count), default=None)
                    if cover:
                        old.remove(cover)
                    elif count:
                        flags.append(("retry", path, row[2], f"test retry added: {row[3].strip()}"))
                        break
        if path.rsplit("/", 1)[-1] == "verify.json":
            # An added observe line counts unless it replaces an observe line of the same package
            # (an edit such as a trailing comma); observe moved to another package counts.
            for gone, row in changed_pairs(hunks):
                if COMMENT.match(row[3]) or not OBSERVE.search(row[3]):
                    continue
                if gone and OBSERVE.search(gone[3]) and PACKAGE_NAME.findall(gone[3]) == PACKAGE_NAME.findall(row[3]):
                    continue
                flags.append(("observe", path, row[2], f"pure-core rule set to observe: {row[3].strip()}"))
            names = Counter(m[1] for r in added_code for m in PACKAGE_NAME.finditer(r[3]))
            for row in removed_code:
                for m in PACKAGE_NAME.finditer(row[3]):
                    if names[m[1]]:
                        names[m[1]] -= 1
                    else:
                        flags.append(("removed", path, row[1], f"package removed from verify.json: {row[3].strip()}"))
        for prefix, pattern, what in checks:
            kept = Counter(m for r in removed_code for m in markers(pattern, r[3]))
            for row in added_code:
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
