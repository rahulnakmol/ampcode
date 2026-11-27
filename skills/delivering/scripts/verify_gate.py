#!/usr/bin/env python3
"""Run and check the verification gate before a pull request: per package, cheap checks, a pure
core and end-to-end tests, with evidence bound to the exact commit.

  python3 verify_gate.py core  [--repo .] [--rev <rev>] [--package <name> ...]
  python3 verify_gate.py run   [--repo .] [--base <rev>] [--package <name> ...] [--out <dir>]
  python3 verify_gate.py check --base <rev> [--head HEAD] [--repo .] [--out <dir>]

The repository's verify.json lists its packages (one for a single repository, one per package in
a monorepo); ../reference/verification.md gives the format.

core:  scans each package's core paths (Python, JavaScript/TypeScript, Go) and prints one line
       per violation: an I/O module imported, a side effect called (print, fetch, time.Now ...), or
       an import of code outside the core (dependencies point inward). Exits 1 when a package in
       "enforce" mode has a violation, or a core path holds no source files; "observe" packages
       print their violations and never fail. Reads the worktree, or the commit given by --rev.
run:   for each package (all, the named ones, or those base...HEAD changed), runs its checks,
       then core, then e2e, from the repository root, stopping at the first failure. Writes
       <out>/<package>.json and .log, bound to HEAD. Refuses a worktree with uncommitted changes.
check: for every package base...head changed: passing evidence on head, made with the package
       definition that judges the change (verify.json at base when base has it, so a change
       cannot edit its own judge), an e2e step that ran and passed, and core passing at head.
       A changed file outside every package fails unless verify.json's "ignore" covers it.
       Exits 0 and prints "pass" only when every changed package passes.

Default <out> is the worktree's own git directory (`git rev-parse --git-path verify`), so
evidence is never committed. Standard library only. The core scan reads text patterns, not a
language's syntax: a pass means no pattern matched, not that the core is pure.
"""

import argparse
import ast
import datetime
import fnmatch
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
import time

MANIFEST = "verify.json"
CODE = {".py": "py", ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js", ".ts": "js", ".tsx": "js",
        ".mts": "js", ".cts": "js", ".go": "go"}
TEST_FILE = re.compile(r"(?:^|/)(?:test_[^/]*\.py|[^/]*_test\.(?:py|go)|conftest\.py|[^/]*\.(?:test|spec)\.[cm]?[jt]sx?)$"
                       r"|(?:^|/)(?:__tests__|testdata|tests?)/")
SKIP_DIRS = {".git", "node_modules", "vendor", "__pycache__", "dist", "build", ".venv"}

IO_MODULES = {
    "py": {"os", "sys", "subprocess", "socket", "shutil", "pathlib", "io", "tempfile", "glob", "sqlite3", "http",
           "urllib", "requests", "httpx", "aiohttp", "asyncio", "logging", "threading", "multiprocessing", "signal",
           "smtplib", "ftplib", "select", "selectors", "shelve", "dbm", "webbrowser", "ctypes", "boto3", "openai",
           "anthropic", "psycopg", "psycopg2", "sqlalchemy", "redis", "pymongo"},
    "js": {"fs", "fs/promises", "child_process", "net", "http", "https", "http2", "dgram", "dns", "tls", "os",
           "process", "readline", "worker_threads", "cluster", "axios", "node-fetch", "undici", "pg", "mysql",
           "mysql2", "mongodb", "mongoose", "redis", "ioredis", "@prisma/client", "openai", "@anthropic-ai/sdk",
           "ws", "sqlite3", "better-sqlite3", "bun:sqlite"},
    "go": {"os", "os/exec", "os/signal", "net", "net/http", "net/rpc", "net/smtp", "io/ioutil", "database/sql",
           "log", "log/slog", "math/rand", "math/rand/v2", "crypto/rand", "syscall", "plugin",
           "github.com/sashabaranov/go-openai", "github.com/openai/openai-go",
           "github.com/anthropics/anthropic-sdk-go", "github.com/jackc/pgx/v5", "gorm.io/gorm",
           "github.com/redis/go-redis/v9"},
}
IO_PREFIXES = {"js": ("@aws-sdk/", "@azure/", "@google-cloud/"), "py": (), "go": ("github.com/aws/aws-sdk-go",)}
SIDE_EFFECTS = {
    "py": r"(?<![\w.])(?:open|print|input)\s*\(",
    "js": r"(?<![\w.])fetch\s*\(|\bconsole\.\w+|(?<![\w.])process\.\w+|\bDate\.now\s*\(|\bnew\s+Date\s*\(\s*\)"
          r"|\bMath\.random\s*\(|\brandomUUID\s*\(|(?<![\w.])set(?:Timeout|Interval)\s*\(|\b(?:localStorage|sessionStorage|document|window)\.\w+"
          r"|\bXMLHttpRequest\b|(?<![\w.])(?:Bun|Deno)\.\w+",
    "go": r"\btime\.(?:Now|Since|Until|Sleep|After|Tick|NewTimer|NewTicker)\s*\(|\bfmt\.(?:Print|Scan)\w*\s*\(",
}
# Python clock and randomness calls, by the full name a call resolves to through its imports and
# aliases: `from time import time as now; now()` is time.time.
PY_CLOCK = re.compile(r"^(?:time\.(?:time|time_ns|sleep|monotonic|monotonic_ns|perf_counter|perf_counter_ns|localtime|ctime)"
                      r"|random\.(?!Random$)\w+|secrets\.\w+|uuid\.uuid[14]|datetime\.(?:datetime|date)\.(?:now|utcnow|today))$")
# The same calls as text, for a file Python cannot parse.
PY_CLOCK_TEXT = (r"\b(?:datetime|date)\.(?:now|utcnow|today)\s*\(|\btime\.(?:time|sleep|monotonic)\s*\("
                 r"|\brandom\.\w+\s*\(|\buuid\.uuid[14]\s*\(")
NON_CODE = re.compile(r"\.(?:json|css|scss|svg|png|txt|md|ya?ml|html)$")


def git(repo, *args):
    run = subprocess.run(["git", "-C", repo, *args], capture_output=True)
    return run.stdout.decode("utf-8", "replace") if run.returncode == 0 else None


def rev_commit(repo, rev):
    out = git(repo, "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    return out.strip() if out else None


class Tree:
    """Files of the worktree (rev None) or of one commit."""

    def __init__(self, repo, rev=None):
        self.repo, self.rev = repo, rev
        if rev:
            self.files = set((git(repo, "ls-tree", "-r", "--name-only", rev) or "").splitlines())
        else:
            self.files = set()
            for root, dirs, names in os.walk(repo):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                for name in names:
                    self.files.add(os.path.relpath(os.path.join(root, name), repo).replace(os.sep, "/"))

    def read(self, path):
        if self.rev:
            return git(self.repo, "show", f"{self.rev}:{path}")
        with open(os.path.join(self.repo, path), encoding="utf-8", errors="replace") as handle:
            return handle.read()

    def under(self, path):
        path = path.strip("/")
        return sorted(f for f in self.files if path in ("", ".") or f == path or f.startswith(path + "/"))

    def is_dir(self, path):
        return any(f.startswith(path.rstrip("/") + "/") for f in self.files)


# ---------------------------------------------------------------- the core scan

def blank(match):
    """Replace a match with spaces, keeping its newlines so line numbers hold."""
    return re.sub(r"[^\n]", " ", match.group(0))


def expression_end(token, i):
    """Index just past the } that closes the ${ expression starting at i, skipping strings and comments."""
    depth, j = 0, i + 1
    while j < len(token) - 1:
        c = token[j]
        if c in "\"'`":
            j += 1
            while j < len(token) - 1 and token[j] != c:
                j += 2 if token[j] == "\\" else 1
        elif token.startswith("//", j):
            j = token.find("\n", j) if "\n" in token[j:] else len(token) - 2
        elif token.startswith("/*", j):
            j = token.find("*/", j) + 1 if "*/" in token[j:] else len(token) - 2
        elif c in "{}":
            depth += 1 if c == "{" else -1
            if not depth:
                return j + 1
        j += 1
    return len(token) - 1


def template_code(token):
    """A JavaScript template literal with its text blanked and its ${...} expressions kept.

    An escaped \\${ is text. Braces inside strings and comments in an expression do not close it.
    """
    out, i = [token[0]], 1
    while i < len(token) - 1:
        if token[i] == "\\":
            out.append("  " if token[i + 1] != "\n" else " \n")
            i += 2
        elif token.startswith("${", i):
            j = expression_end(token, i)
            out.append("${" + code_only(token[i + 2:j - 1], "js") + token[j - 1])
            i = j
        else:
            out.append(token[i] if token[i] == "\n" else " ")
            i += 1
    return "".join(out)[:len(token) - 1] + token[-1]


def code_only(text, lang, keep_strings=False):
    """Text with comments blanked, and string contents too unless keep_strings; line numbers kept.

    A JavaScript template literal keeps its ${...} expressions, which are code.
    """
    strings = [r'"""[\s\S]*?"""', r"'''[\s\S]*?'''"] if lang == "py" else [r"`(?:\\[\s\S]|[^`\\])*`"]
    strings += [r'"(?:\\.|[^"\\\n])*"', r"'(?:\\.|[^'\\\n])*'"]
    comments = [r"#[^\n]*"] if lang == "py" else [r"/\*[\s\S]*?\*/", r"//[^\n]*"]
    pattern = re.compile("|".join(f"(?:{p})" for p in strings + comments))

    def keep(match):
        token = match.group(0)
        if token[0] not in "\"'`":
            return blank(match)
        if keep_strings:
            return token
        if token[0] == "`" and lang == "js":
            return template_code(token)
        q = 3 if token[:3] in ('"""', "'''") else 1
        return token[:q] + blank(re.match(r"[\s\S]*", token[q:-q])) + token[-q:]
    return pattern.sub(keep, text)


def py_imports(text):
    """[(line, module)] from Python's own parser; the pattern fallback for a file it cannot parse."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        found, code = [], code_only(text, "py")
        for m in re.finditer(r"^[ \t]*(?:from[ \t]+(\.*[\w.]*)[ \t]+import\b|import[ \t]+([\w., \t]+))", code, re.M):
            line = code.count("\n", 0, m.start()) + 1
            names = [m[1]] if m[1] is not None else [n.split()[0] for n in m[2].split(",") if n.strip()]
            found += [(line, n) for n in names]
        return found
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, alias.name) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            found.append((node.lineno, "." * node.level + (node.module or "")))
    return found


def py_clock_calls(text):
    """[(line, full name)] of each clock or randomness call, resolved through imports and aliases;
    None when Python cannot parse the file."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    names = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                names[a.asname or a.name.split(".")[0]] = a.name if a.asname else a.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for a in node.names:
                names[a.asname or a.name] = f"{node.module}.{a.name}"
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            parts, func = [], node.func
            while isinstance(func, ast.Attribute):
                parts.append(func.attr)
                func = func.value
            if isinstance(func, ast.Name) and func.id in names:
                full = ".".join([names[func.id], *reversed(parts)])
                if PY_CLOCK.match(full):
                    found.append((node.lineno, full))
    return sorted(found)


IMPORT = {
    "js": re.compile(r"(?:\bfrom\s*|^\s*import\s*|\brequire\s*\(\s*|\bimport\s*\(\s*)(['\"])([^'\"\n]+)\1", re.M),
    "go": re.compile(r"^[ \t]*import\s*\(([^)]*)\)|^[ \t]*import\s+(?:[\w.]+\s+)?\"([^\"]+)\"", re.M),
}


def imports(text, lang):
    """[(line, module)] imported by the file; relative modules keep their dots or ./ prefix.

    JavaScript and Go imports are read with comments removed, and count only where their keyword
    is code, not text inside a string.
    """
    if lang == "py":
        return py_imports(text)
    plain, masked, found = code_only(text, lang, keep_strings=True), code_only(text, lang), []
    for m in IMPORT[lang].finditer(plain):
        word = m.start() + len(m.group(0)) - len(m.group(0).lstrip())
        if masked[word] != plain[word]:
            continue  # the keyword is inside a string
        line = plain.count("\n", 0, m.start()) + 1
        if lang == "js":
            found.append((line, m[2]))
        elif m[2]:
            found.append((line, m[2]))
        else:
            for s in re.finditer(r"(?:[\w.]+\s+)?\"([^\"]+)\"", m[1]):
                found.append((plain.count("\n", 0, m.start(1) + s.start()) + 1, s[1]))
    return found


def go_module(tree, path):
    """(module path, its directory) from the nearest go.mod at or above path."""
    parts = path.split("/")
    for i in range(len(parts), -1, -1):
        candidate = "/".join(parts[:i] + ["go.mod"])
        if candidate in tree.files:
            m = re.search(r"^module\s+(\S+)", tree.read(candidate) or "", re.M)
            if m:
                return m[1], "/".join(parts[:i])
    return None, None


def local_target(tree, file, lang, module):
    """The repository path an import names, or None for a library or the standard library."""
    here = posixpath.dirname(file)
    if lang == "js":
        if not module.startswith("."):
            return None
        return posixpath.normpath(posixpath.join(here, module))
    if lang == "go":
        mod, root = go_module(tree, file)
        if mod and (module == mod or module.startswith(mod + "/")):
            return posixpath.normpath(posixpath.join(root, module[len(mod):].lstrip("/")))
        return None
    dots = len(module) - len(module.lstrip("."))
    rest = module[dots:].replace(".", "/")
    if dots:
        base = here
        for _ in range(dots - 1):
            base = posixpath.dirname(base)
        return posixpath.normpath(posixpath.join(base, rest)) if rest else base
    for root in ("", "src/"):
        target = root + rest
        if f"{target}.py" in tree.files or tree.is_dir(target):
            return target
    return None


def inside(path, roots):
    """Whether path (a file, a directory, or a module path without its extension) is in a root."""
    for root in roots:
        bare = re.sub(r"\.(?:py|go|[cm]?[jt]sx?)$", "", root)
        if path in (root, bare) or path.startswith(root.rstrip("/") + "/"):
            return True
    return False


def scan_file(tree, file, core):
    lang = CODE[os.path.splitext(file)[1]]
    text = tree.read(file) or ""
    stripped = code_only(text, lang)
    out = []
    for line, module in imports(text, lang):
        name = module[5:] if lang == "js" and module.startswith("node:") else module
        top = name.split(".")[0] if lang == "py" else name.split("/")[0] if lang == "js" else name
        if name in IO_MODULES[lang] or top in IO_MODULES[lang] or name.startswith(IO_PREFIXES[lang]):
            out.append((file, line, "io-import", f"imports {module}, an I/O module; move the call to the shell"))
            continue
        target = local_target(tree, file, lang, module)
        if target and not NON_CODE.search(target) and not inside(target, core):
            out.append((file, line, "outward-import",
                        f"imports {target}, outside the core; dependencies point inward, so pass its result in"))
    for m in re.finditer(SIDE_EFFECTS[lang], stripped):
        line = stripped.count("\n", 0, m.start()) + 1
        out.append((file, line, "side-effect", f"calls {m.group(0).strip()}; side effects belong in the shell"))
    clocks = py_clock_calls(text) if lang == "py" else []
    if clocks is None:
        clocks = [(stripped.count("\n", 0, m.start()) + 1, m.group(0).rstrip("( "))
                  for m in re.finditer(PY_CLOCK_TEXT, stripped)]
    for line, name in clocks:
        out.append((file, line, "side-effect", f"calls {name}(; pass the time or random value in"))
    return out


def scan_core(tree, package):
    """(violations, problems) for one package's core paths."""
    core = [c.strip("/") for c in package.get("core") or []]
    violations, problems = [], []
    if not core:
        problems.append("no core paths: list the pure domain code under \"core\"")
    for root in core:
        files = [f for f in tree.under(root) if os.path.splitext(f)[1] in CODE and not TEST_FILE.search(f)]
        if not files:
            problems.append(f"core path {root} holds no source files: the check would pass on nothing")
        for file in files:
            violations += scan_file(tree, file, core)
    return sorted(set(violations)), problems


def core_report(name, mode, violations, problems):
    lines = [f"{name}: {p}" for p in problems]
    tag = "observe: " if mode == "observe" else ""
    lines += [f"{tag}{name}: {f}:{n}: {kind}: {what}" for f, n, kind, what in violations]
    failed = bool(problems) or (bool(violations) and mode != "observe")
    return lines, failed


# ---------------------------------------------------------------- the manifest

def parse_manifest(text, where):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise SystemExit(f"{where}: not JSON: {error}")
    packages = data.get("packages") if isinstance(data, dict) else None
    if not isinstance(packages, list) or not packages:
        raise SystemExit(f"{where}: needs a non-empty \"packages\" list")
    out = {}
    for p in packages:
        if not isinstance(p, dict) or not p.get("name") or not isinstance(p.get("path"), str):
            raise SystemExit(f"{where}: each package needs \"name\" and \"path\"")
        if p.get("mode", "enforce") not in ("enforce", "observe"):
            raise SystemExit(f"{where}: {p['name']}: \"mode\" is \"enforce\" or \"observe\"")
        out[p["name"]] = p
    return out, list(data.get("ignore") or [])


def judges(repo, base, head=None):
    """({name: package definition that judges the change}, ignore globs, notes, new package names).

    verify.json at base judges when base has it; a package new at head is judged by head's
    definition, and the notes say so for the reviewer. Without head, head is the worktree.
    """
    if head:
        head_text = git(repo, "show", f"{head}:{MANIFEST}")
    elif os.path.exists(os.path.join(repo, MANIFEST)):
        with open(os.path.join(repo, MANIFEST), encoding="utf-8") as handle:
            head_text = handle.read()
    else:
        head_text = None
    base_text = git(repo, "show", f"{base}:{MANIFEST}") if base else None
    if head_text is None and base_text is None:
        raise SystemExit(f"no {MANIFEST} in {repo}: write one (see reference/verification.md)")
    head, head_ignore = parse_manifest(head_text, f"{MANIFEST} at HEAD") if head_text else ({}, [])
    if base_text is None:
        notes = [f"{MANIFEST} is new in this change: its definitions judge it; the reviewer reads them"] if base else []
        return head, head_ignore, notes, set()
    packages, ignore = parse_manifest(base_text, f"{MANIFEST} at {base}")
    notes, new = [], set()
    for name, p in head.items():
        if name not in packages:
            packages[name] = p
            new.add(name)
            notes.append(f"{name}: new package, defined by this change; the reviewer reads its definition")
        elif fingerprint(p) != fingerprint(packages[name]):
            notes.append(f"{name}: this change edits its definition; {MANIFEST} at base judges it")
    return packages, ignore, notes, new


def fingerprint(package):
    return hashlib.sha256(json.dumps(package, sort_keys=True).encode()).hexdigest()[:16]


def owners(path, packages, new=()):
    """The packages that must pass for a change to path: the deepest package that existed at
    base, and the deepest new package. A new package cannot take files from their base judge,
    and a new nested package is still judged itself.
    """
    old = longest(path, {n: p for n, p in packages.items() if n not in new})
    added = longest(path, {n: packages[n] for n in new})
    return [p for p in (old, added) if p]


def longest(path, packages):
    best = None
    for p in packages.values():
        root = p["path"].strip("/")
        if root in ("", ".") or path == root or path.startswith(root + "/"):
            if best is None or len(root.strip(".")) > len(best["path"].strip("/").strip(".")):
                best = p
    return best


def changed(repo, base, head, packages, ignore, new=()):
    """({package names changed}, [files outside every package and not ignored]).

    Renames count as a deletion and an addition, so a move changes both packages.
    """
    names, outside = set(), []
    for path in (git(repo, "diff", "--name-only", "--no-renames", f"{base}...{head}") or "").splitlines():
        if path == MANIFEST:
            continue  # judged at base; judges() notes each edited definition
        found = owners(path, packages, new)
        if found:
            names.update(p["name"] for p in found)
        elif not any(fnmatch.fnmatch(path, g) for g in ignore):
            outside.append(path)
    return names, outside


def out_dir(repo, out):
    if out:
        return out
    path = (git(repo, "rev-parse", "--git-path", "verify") or "").strip()
    return path if os.path.isabs(path) else os.path.join(repo, path)


# ---------------------------------------------------------------- commands

def cmd_core(args):
    tree = Tree(args.repo, args.rev)
    packages = judges(args.repo, None, args.rev)[0]
    failed = False
    for name in args.package or list(packages):
        if name not in packages:
            raise SystemExit(f"no package {name!r} in {MANIFEST}")
        p = packages[name]
        lines, bad = core_report(name, p.get("mode", "enforce"), *scan_core(tree, p))
        print("\n".join(lines) or f"{name}: core pass")
        failed |= bad
    print("fail" if failed else "pass")
    return 1 if failed else 0


def cmd_run(args):
    head = rev_commit(args.repo, "HEAD")
    if git(args.repo, "status", "--porcelain", "--untracked-files=no"):
        print("uncommitted changes: commit first, so the evidence binds to a commit")
        return 1
    packages, ignore, notes, new = judges(args.repo, args.base)
    for note in notes:
        print(f"note: {note}")
    names = args.package or (sorted(changed(args.repo, args.base, head, packages, ignore, new)[0]) if args.base
                             else list(packages))
    directory = out_dir(args.repo, args.out)
    os.makedirs(directory, exist_ok=True)
    failed = False
    for name in names:
        if name not in packages:
            raise SystemExit(f"no package {name!r} in {MANIFEST}")
        p = packages[name]
        log_path = os.path.join(directory, f"{name}.log")
        steps, passed = [], True
        with open(log_path, "w", encoding="utf-8") as log:
            plan = [("check", c) for c in p.get("checks") or []] + [("core", None)]
            plan += [("e2e", p["e2e"])] if p.get("e2e") else []
            for step, command in plan:
                start = time.monotonic()
                if step == "core":
                    lines, bad = core_report(name, p.get("mode", "enforce"), *scan_core(Tree(args.repo, head), p))
                    log.write("$ core\n" + "\n".join(lines) + "\n")
                    code = 1 if bad else 0
                else:
                    log.write(f"$ {command}\n")
                    log.flush()
                    code = subprocess.run(command, shell=True, cwd=args.repo, stdout=log, stderr=subprocess.STDOUT).returncode
                steps.append({"step": step, "command": command or "verify_gate.py core", "exit": code,
                              "seconds": round(time.monotonic() - start, 1)})
                print(f"{name}: {step}: {command or 'core'}: exit {code}")
                if not code and (rev_commit(args.repo, "HEAD") != head
                                 or git(args.repo, "status", "--porcelain", "--untracked-files=no")):
                    print(f"{name}: {step} changed HEAD or tracked files, so later steps would not test {head[:12]}")
                    code = steps[-1]["exit"] = 1
                if code:
                    passed = False
                    break
        if not p.get("e2e"):
            print(f"{name}: no \"e2e\" command: every package needs end-to-end tests")
            passed = False
        evidence = {"package": name, "head": head, "definition": fingerprint(p), "steps": steps, "passed": passed,
                    "log": log_path, "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
        with open(os.path.join(directory, f"{name}.json"), "w", encoding="utf-8") as handle:
            json.dump(evidence, handle, indent=2)
        print(f"{name}: {'passed' if passed else 'failed'} on {head[:12]}; evidence {os.path.join(directory, name)}.json")
        failed |= not passed
    if not names:
        print("no package changed")
    print("fail" if failed else "pass")
    return 1 if failed else 0


def cmd_check(args):
    base, head = rev_commit(args.repo, args.base), rev_commit(args.repo, args.head)
    if not base or not head:
        print(f"cannot resolve --base {args.base} or --head {args.head}: not run")
        return 1
    packages, ignore, notes, new = judges(args.repo, base, head)
    for note in notes:
        print(f"note: {note}")
    names, outside = changed(args.repo, base, head, packages, ignore, new)
    problems = [f"{path}: changed, but outside every package and not under \"ignore\"" for path in outside]
    directory = out_dir(args.repo, args.out)
    tree = Tree(args.repo, head)
    for name in sorted(names):
        p = packages[name]
        try:
            with open(os.path.join(directory, f"{name}.json"), encoding="utf-8") as handle:
                ev = json.load(handle)
        except (OSError, json.JSONDecodeError):
            problems.append(f"{name}: no evidence: run verify_gate.py run on this head")
            continue
        steps = {s.get("step"): s for s in ev.get("steps") or []}
        if ev.get("head") != head:
            problems.append(f"{name}: evidence is for {str(ev.get('head'))[:12]}, not head {head[:12]}: run again")
        elif ev.get("definition") != fingerprint(p):
            problems.append(f"{name}: evidence ran another definition than the one that judges this change: run again")
        elif not p.get("e2e") or steps.get("e2e", {}).get("exit") != 0:
            problems.append(f"{name}: no passing e2e step in the evidence")
        elif not ev.get("passed"):
            problems.append(f"{name}: the evidence failed: see {ev.get('log')}")
        lines, bad = core_report(name, p.get("mode", "enforce"), *scan_core(tree, p))
        if bad:
            problems += lines
        elif lines:
            print("\n".join(lines))
        if not any(x.startswith(f"{name}:") for x in problems):
            print(f"{name}: pass (evidence {ev.get('at')}, {len(ev.get('steps') or [])} steps on {head[:12]})")
    if not names and not outside:
        print("no package changed")
    for problem in problems:
        print(problem)
    print("fail" if problems else "pass")
    return 1 if problems else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    core = sub.add_parser("core", help="scan the core paths for I/O, side effects and outward imports")
    core.add_argument("--rev", help="scan this commit instead of the worktree")
    run = sub.add_parser("run", help="run checks, core and e2e; write evidence bound to HEAD")
    run.add_argument("--base", help="run only the packages base...HEAD changed, judged by verify.json at base")
    run.add_argument("--out")
    check = sub.add_parser("check", help="check the evidence for every package base...head changed")
    check.add_argument("--base", required=True)
    check.add_argument("--head", default="HEAD")
    check.add_argument("--out")
    for p in (core, run):
        p.add_argument("--package", action="append", help="only this package (repeatable)")
    for p in (core, run, check):
        p.add_argument("--repo", default=".")
    args = parser.parse_args(argv)
    args.repo = os.path.abspath(args.repo)
    return {"core": cmd_core, "run": cmd_run, "check": cmd_check}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
