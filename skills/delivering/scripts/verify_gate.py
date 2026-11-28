#!/usr/bin/env python3
"""Run and check the verification gate before a pull request: per package, cheap checks, a pure
core and end-to-end tests, with evidence bound to the exact commit.

  python3 verify_gate.py core  [--repo .] [--rev <rev>] [--package <name> ...]
  python3 verify_gate.py run   [--repo .] [--base <rev>] [--package <name> ...] [--out <dir>]
  python3 verify_gate.py check --base <rev> [--head HEAD] [--repo .] [--out <dir>]

The repository's verify.json lists its packages (one for a single repository, one per package in
a monorepo); ../reference/verification.md gives the format.

core:  scans each package's core paths (Python, JavaScript/TypeScript, Go, C#, Rust) and prints one line
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
        ".mts": "js", ".cts": "js", ".go": "go", ".cs": "cs", ".rs": "rs"}
TEST_FILE = re.compile(r"(?:^|/)(?:test_[^/]*\.py|[^/]*_test\.(?:py|go)|conftest\.py|[^/]*\.(?:test|spec)\.[cm]?[jt]sx?"
                       r"|[^/]*Tests?\.cs)$|(?:^|/)(?:__tests__|testdata|tests?|benches|[^/]*\.Tests?)/")
SKIP_DIRS = {".git", "node_modules", "vendor", "__pycache__", "dist", "build", ".venv", "bin", "obj", "target"}

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
# C# namespaces and Rust paths that do I/O, clock or randomness: a match is the name itself or
# anything under it (System.IO covers System.IO.Compression; std::fs covers std::fs::File).
IO_SCOPES = {
    "cs": ("System.IO", "System.Net", "System.Data", "System.Diagnostics.Eventing", "System.Management", "Microsoft.Win32",
           "Microsoft.Data", "Microsoft.EntityFrameworkCore", "Microsoft.Extensions.Logging",
           "Microsoft.Extensions.Configuration", "Microsoft.AspNetCore", "Dapper", "Npgsql", "MySql", "MySqlConnector",
           "StackExchange.Redis", "MongoDB", "Serilog", "NLog", "Azure", "Amazon", "Google.Cloud", "RestSharp",
           "Grpc.Net.Client", "OpenAI", "Anthropic"),
    "rs": ("std::fs", "std::net", "std::process", "std::env", "std::io", "std::os", "std::thread", "tokio", "async_std",
           "reqwest", "hyper", "ureq", "sqlx", "diesel", "rusqlite", "redis", "mongodb", "rand", "getrandom", "log",
           "tracing", "env_logger", "openai", "async_openai"),
}
SIDE_EFFECTS = {
    "py": r"(?<![\w.])(?:open|print|input)\s*\(",
    "js": r"(?<![\w.])fetch\s*\(|\bconsole\.\w+|(?<![\w.])process\.\w+|\bDate\.now\s*\(|\bnew\s+Date\s*\(\s*\)"
          r"|\bMath\.random\s*\(|\brandomUUID\s*\(|(?<![\w.])set(?:Timeout|Interval)\s*\(|\b(?:localStorage|sessionStorage|document|window)\.\w+"
          r"|\bXMLHttpRequest\b|(?<![\w.])(?:Bun|Deno)\.\w+",
    "go": r"\btime\.(?:Now|Since|Until|Sleep|After|Tick|NewTimer|NewTicker)\s*\(|\bfmt\.(?:Print|Scan)\w*\s*\(",
    "cs": r"(?<![\w.])(?:System\.(?:IO\.)?)?(?:Console|File|Directory)\.\w+|(?<![\w.])(?:System\.)?Environment\."
          r"(?:GetEnvironmentVariable\w*|SetEnvironmentVariable|Exit|CurrentDirectory|GetCommandLineArgs|TickCount\w*"
          r"|MachineName|UserName|ProcessId|GetFolderPath)\b|\b(?:DateTime|DateTimeOffset)\.(?:Now|UtcNow|Today)\b"
          r"|\bStopwatch\.\w+|\bGuid\.NewGuid\s*\(|\bnew\s+(?:System\.)?Random\s*\(|\bRandom\.Shared\b"
          r"|\bRandomNumberGenerator\.\w+|\bProcess\.(?:Start|GetCurrentProcess|Kill)\b|\b(?:Thread\.Sleep|Task\.Delay)\s*\("
          r"|\bTimeProvider\.System\b|\b(?:Debug|Trace)\.Write\w*|\bnew\s+(?:[\w.]+\.)?(?:HttpClient|WebClient|TcpClient"
          r"|UdpClient|Socket|SqlConnection|SqliteConnection|NpgsqlConnection|FileStream|StreamReader|StreamWriter)\s*\(",
    "rs": r"(?<![\w:])(?:println|print|eprintln|eprint|dbg)!|\b(?:SystemTime|Instant|Utc|Local|OffsetDateTime)::now\w*\s*\("
          r"|\bthread_rng\s*\(|\bUuid::new_v[47]\s*\(|\bOsRng\b",
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
        """The file's text, without a leading byte-order mark (common in C# files)."""
        if self.rev:
            text = git(self.repo, "show", f"{self.rev}:{path}")
        else:
            with open(os.path.join(self.repo, path), encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        return text[1:] if text and text.startswith("\ufeff") else text

    def under(self, path):
        path = path.strip("/")
        return sorted(f for f in self.files if path in ("", ".") or f == path or f.startswith(path + "/"))

    def is_dir(self, path):
        return any(f.startswith(path.rstrip("/") + "/") for f in self.files)


# ---------------------------------------------------------------- the core scan

def blank(match):
    """Replace a match with spaces, keeping its newlines so line numbers hold."""
    return re.sub(r"[^\n]", " ", match.group(0))


JS_BEFORE_REGEX = {"", *"(,=:[!&|?{};+-*%<>~^"}
JS_KEYWORDS_BEFORE_REGEX = {"return", "typeof", "case", "in", "of", "yield", "await", "delete", "void", "throw", "new", "else", "do"}


def js_code(text, keep_strings=False):
    """JavaScript or TypeScript with comments blanked, and string, template and regular expression
    text too unless keep_strings; ${...} expressions (nested templates included) stay code.
    Same length as text, so offsets and line numbers hold."""
    out, n = list(text), len(text)

    def clear(a, b):
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    def template(i):
        j = i + 1
        while j < n:
            if text[j] == "\\":
                if not keep_strings:
                    clear(j, j + 2)
                j += 2
            elif text[j] == "`":
                return j + 1
            elif text.startswith("${", j):
                j = code(j + 2, True)
            else:
                if not keep_strings:
                    clear(j, j + 1)
                j += 1
        return n

    def code(i, in_expression):
        # prev is the last token; parens records whether each open ( follows if, while, for or
        # with, after whose ) a slash starts a regex literal.
        depth, prev, parens = 0, "", []
        while i < n:
            c = text[i]
            if text.startswith("//", i):
                j = text.find("\n", i)
                j = n if j < 0 else j
                clear(i, j)
                i = j
            elif text.startswith("/*", i):
                j = text.find("*/", i + 2)
                j = n if j < 0 else j + 2
                clear(i, j)
                i = j
            elif c in "\"'":
                j = i + 1
                while j < n and text[j] not in (c, "\n"):
                    j += 2 if text[j] == "\\" else 1
                if not keep_strings:
                    clear(i + 1, j)
                i, prev = j + 1, ")"
            elif c == "`":
                i, prev = template(i), ")"
            elif c == "/" and (prev in JS_BEFORE_REGEX or prev in JS_KEYWORDS_BEFORE_REGEX):
                j, in_class = i + 1, False
                while j < n and text[j] != "\n" and (in_class or text[j] != "/"):
                    in_class = (in_class or text[j] == "[") and text[j] != "]"
                    j += 2 if text[j] == "\\" else 1
                if not keep_strings:
                    clear(i + 1, j)
                i, prev = j + 1, ")"
            elif c.isalnum() or c in "_$":
                j = i
                while j < n and (text[j].isalnum() or text[j] in "_$"):
                    j += 1
                i, prev = j, text[i:j]
            elif text.startswith(("++", "--"), i):
                i, prev = i + 2, ")"  # x++ / y divides
            elif c in "()":
                if c == "(":
                    parens.append(prev in ("if", "while", "for", "with"))
                    prev = "("
                else:
                    prev = "(" if parens and parens.pop() else ")"
                i += 1
            else:
                if in_expression and c in "{}":
                    if c == "}" and not depth:
                        return i + 1
                    depth += 1 if c == "{" else -1
                if not c.isspace():
                    prev = c
                i += 1
        return n

    code(0, False)
    return "".join(out)


def code_only(text, lang, keep_strings=False):
    """Text with comments blanked, and string contents too unless keep_strings; line numbers kept."""
    if lang == "js":
        return js_code(text, keep_strings)
    if lang in ("cs", "rs"):
        return cs_rs_code(text, lang, keep_strings)
    # A Go raw string has no escapes: a backslash in it is text.
    strings = [r'"""[\s\S]*?"""', r"'''[\s\S]*?'''"] if lang == "py" else [r"`[^`]*`"]
    strings += [r'"(?:\\.|[^"\\\n])*"', r"'(?:\\.|[^'\\\n])*'"]
    comments = [r"#[^\n]*"] if lang == "py" else [r"/\*[\s\S]*?\*/", r"//[^\n]*"]
    pattern = re.compile("|".join(f"(?:{p})" for p in strings + comments))

    def keep(match):
        token = match.group(0)
        if token[0] not in "\"'`":
            return blank(match)
        if keep_strings:
            return token
        q = 3 if token[:3] in ('"""', "'''") else 1
        return token[:q] + blank(re.match(r"[\s\S]*", token[q:-q])) + token[-q:]
    return pattern.sub(keep, text)


CS_RS_TOKENS = {
    # C#: raw """...""" strings, verbatim @"..." (a "" is a quote), regular strings, chars.
    "cs": [r'(?P<p>\$*)"""[\s\S]*?"""+', r'(?P<v>\$@|@\$|@)"(?:[^"]|"")*"', r'(?P<r>\$?)"(?:\\.|[^"\\\n])*"',
           r"'(?:\\.[^'\n]*|[^'\\\n])'"],
    # Rust: raw strings r#"..."#, strings that may span lines, chars (not lifetimes such as 'a).
    "rs": [r'b?r(?P<h>#*)"[\s\S]*?"(?P=h)', r'b?"(?:\\[\s\S]|[^"\\])*"', r"b?'(?:\\.[^'\n]*|[^'\\\n])'"],
}


def cs_rs_code(text, lang, keep_strings):
    """C# or Rust with comments blanked, and string text too unless keep_strings; the {...} holes
    of a C# interpolated string ($"...") stay code. Rust #[cfg(test)] modules are blanked: test code
    is not core. Same length as text."""
    pattern = re.compile("|".join(f"(?:{p})" for p in CS_RS_TOKENS[lang] + [r"/\*[\s\S]*?\*/", r"//[^\n]*"]))

    def keep(match):
        token = match.group(0)
        if token.startswith(("//", "/*")):
            return blank(match)
        if keep_strings:
            return token
        first = min(i for i in (token.find('"'), token.find("'")) if i >= 0)
        last = max(token.rfind('"'), token.rfind("'"))
        body = token[first + 1:last]
        if lang == "cs" and "$" in token[:first]:
            # Keep each {expression} of an interpolated string; {{ is a literal brace.
            out, depth, i = [], 0, 0
            while i < len(body):
                c = body[i]
                if not depth and body.startswith("{{", i):
                    out.append("  ")
                    i += 2
                    continue
                if c == "{" or depth:
                    depth += {"{": 1, "}": -1}.get(c, 0)
                    out.append(c)
                else:
                    out.append(c if c == "\n" else " ")
                i += 1
            body = "".join(out)
        else:
            body = re.sub(r"[^\n]", " ", body)
        return token[:first + 1] + body + token[last:]
    out = pattern.sub(keep, text)
    if lang == "rs":
        for m in reversed(list(re.finditer(r"#\[cfg\(test\)\]\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+\w+\s*\{", out))):
            depth, j = 1, m.end()
            while j < len(out) and depth:
                depth += {"{": 1, "}": -1}.get(out[j], 0)
                j += 1
            out = out[:m.start()] + re.sub(r"[^\n]", " ", out[m.start():j]) + out[j:]
    return out


def rs_use_paths(code):
    """[(offset, path)] for each path a Rust use or extern crate statement names (code has its
    comments and strings blanked): use a::{b, c::d as e} names a::b and a::c::d; a glob names its
    module."""
    found = []
    for m in re.finditer(r"(?:^|(?<=[;{}]))[ \t]*(?:pub(?:\([^)]*\))?\s+)?(?:use\s+([^;]+);|extern\s+crate\s+(\w+))", code, re.M):
        if m[2]:
            found.append((m.start(2), m[2]))
        else:
            spec = re.sub(r"\s+", "", re.sub(r"\s+as\s+\w+", "", m[1]))
            found += [(m.start(1), path) for path in rs_expand(spec)]
    return found


def rs_expand(spec):
    """The paths one use tree names, from its text without spaces or aliases."""
    items, depth, start = [], 0, 0
    for i, c in enumerate(spec + ","):
        depth += {"{": 1, "}": -1}.get(c, 0)
        if c == "," and not depth:
            items.append(spec[start:i])
            start = i + 1
    out = []
    for item in filter(None, items):
        if "{" in item:
            prefix, inner = item.split("{", 1)
            for sub in rs_expand(inner[:inner.rindex("}")]):
                out.append(prefix.rstrip(":") if sub == "self" else prefix + sub)
        else:
            out.append(re.sub(r"::\*$", "", item))
    return [p.lstrip(":") for p in out if p.strip(":")]


def py_imports(text):
    """[(line, name)] from Python's own parser: each imported module, and module.name for each
    name a `from` import takes. The pattern fallback serves a file Python cannot parse."""
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
            prefix = "." * node.level + (f"{node.module}." if node.module else "")
            found += [(node.lineno, prefix + alias.name) for alias in node.names if alias.name != "*"]
            if any(alias.name == "*" for alias in node.names):
                found.append((node.lineno, "." * node.level + (node.module or "")))
    return found


SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)


def scope_imports(body, names=None, top=True):
    """{bound name: {full names}} a scope's imports may leave bound once its body has run; nested
    scopes keep theirs. An import statement directly in the body replaces what came before it; an
    import inside a block (if, try, with) may or may not run, so it adds to them."""
    names = {} if names is None else names
    for node in body:
        if isinstance(node, SCOPES):
            continue
        for bound, full in bindings(node):
            if top:
                names[bound] = {full}
            else:
                names.setdefault(bound, set()).add(full)
        scope_imports(ast.iter_child_nodes(node), names, top=False)
    return names


def bindings(node):
    """[(bound name, full name)] an import statement binds."""
    if isinstance(node, ast.Import):
        return [(a.asname or a.name.split(".")[0], a.name if a.asname else a.name.split(".")[0]) for a in node.names]
    if isinstance(node, ast.ImportFrom) and node.module and not node.level:
        return [(a.asname or a.name, f"{node.module}.{a.name}") for a in node.names]
    return []


class PyEffects(ast.NodeVisitor):
    """Side-effect calls in a Python file: the builtins open, print and input (also inside
    f-strings), and clock and randomness calls resolved through imports and aliases.

    A scope binds names in source order; a name not yet bound in the current scope, or bound in
    an enclosing scope, has the binding that scope's body leaves (see scope_imports). Importing
    open, print or input from builtins is still the builtin. A class body's names are not
    visible in its methods, as in Python."""

    def __init__(self, tree):
        self.scopes, self.found = [("module", scope_imports(tree.body), {})], []
        self.generic_visit(tree)

    def scoped(self, node):
        body = node.body if isinstance(node.body, list) else [node.body]
        kind = "class" if isinstance(node, ast.ClassDef) else "function"
        self.scopes.append((kind, scope_imports(body), {}))
        self.generic_visit(node)
        self.scopes.pop()

    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = visit_Lambda = scoped

    def bind(self, node):
        for bound, full in bindings(node):
            self.scopes[-1][2][bound] = full

    visit_Import = visit_ImportFrom = bind

    def resolve(self, name):
        """The full names a name may refer to here; {} for a name no import binds."""
        for index in range(len(self.scopes) - 1, -1, -1):
            kind, every, seen = self.scopes[index]
            if kind == "class" and index != len(self.scopes) - 1:
                continue
            if index == len(self.scopes) - 1 and name in seen:
                return {seen[name]}
            if name in every:
                return every[name]
        return set()

    def visit_Call(self, node):
        parts, func = [], node.func
        while isinstance(func, ast.Attribute):
            parts.append(func.attr)
            func = func.value
        if isinstance(func, ast.Name):
            bound = self.resolve(func.id)
            if not bound and not parts and func.id in ("open", "print", "input"):
                self.found.append((node.lineno, f"calls {func.id}(; side effects belong in the shell"))
            for full in sorted(".".join([b, *reversed(parts)]) for b in bound):
                if full in ("builtins.open", "builtins.print", "builtins.input"):
                    self.found.append((node.lineno, f"calls {full}(; side effects belong in the shell"))
                    break
                if PY_CLOCK.match(full):
                    self.found.append((node.lineno, f"calls {full}(; pass the time or random value in"))
                    break
        self.generic_visit(node)


def py_effects(text):
    """[(line, what)] of each side-effect call; None when Python cannot parse the file."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return None
    return sorted(PyEffects(tree).found)


IMPORT = {
    "js": re.compile(r"(?:\bfrom\s*|^\s*import\s*|\brequire\s*\(\s*|\bimport\s*\(\s*)(['\"])([^'\"\n]+)\1", re.M),
    "go": re.compile(r"^[ \t]*import\s*\(([^)]*)\)|^[ \t]*import\s+(?:[\w.]+\s+)?\"([^\"]+)\"", re.M),
}


def imports(text, lang):
    """[(line, module)] imported by the file; relative modules keep their dots or ./ prefix.

    JavaScript, Go, C# and Rust imports are read with comments removed, and count only where their keyword
    is code, not text inside a string.
    """
    if lang == "py":
        return py_imports(text)
    if lang == "cs":
        code = code_only(text, "cs")
        return [(code.count("\n", 0, m.start(1)) + 1, m[1]) for m in re.finditer(
            r"^[ \t]*(?:global\s+)?using\s+(?:static\s+)?(?:\w+\s*=\s*)?(?:global::)?([A-Za-z_][\w.]*)\s*;", code, re.M)]
    if lang == "rs":
        # Use statements, then every path written in code (std::fs::read(...)), outside the uses.
        code = code_only(text, "rs")
        uses = rs_use_paths(code)
        found = [(code.count("\n", 0, at) + 1, path) for at, path in uses]
        rest = re.sub(r"(?:^|(?<=[;{}]))[ \t]*(?:pub(?:\([^)]*\))?\s+)?use\s+[^;]+;", blank, code, flags=re.M)
        found += [(rest.count("\n", 0, m.start()) + 1, m[1].lstrip(":")) for m in re.finditer(
            r"(?<![\w:])((?:::)?[a-z_]\w*(?:::[A-Za-z_]\w*)+)", rest)]
        return found
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


def cs_namespaces(tree):
    """{namespace: [files that declare it]} for the C# files of the tree, read once."""
    if getattr(tree, "_cs_namespaces", None) is None:
        tree._cs_namespaces = {}
        for f in sorted(tree.files):
            if f.endswith(".cs") and not any(part in SKIP_DIRS for part in f.split("/")):
                code = code_only(tree.read(f) or "", "cs")
                for m in re.finditer(r"^[ \t]*namespace\s+([\w.]+)", code, re.M):
                    tree._cs_namespaces.setdefault(m[1], []).append(f)
    return tree._cs_namespaces


def rs_crates(tree):
    """{crate name with - as _: its src directory} from every Cargo.toml [package] in the tree."""
    if getattr(tree, "_rs_crates", None) is None:
        tree._rs_crates = {}
        for f in sorted(tree.files):
            if f.rsplit("/", 1)[-1] == "Cargo.toml":
                m = re.search(r"^\[package\][^\[]*?^name\s*=\s*\"([^\"]+)\"", tree.read(f) or "", re.M | re.S)
                if m:
                    tree._rs_crates[m[1].replace("-", "_")] = posixpath.join(posixpath.dirname(f), "src").lstrip("/")
    return tree._rs_crates


def rs_module_dir(file):
    """The directory that holds a Rust file's child modules: src/a/b.rs has src/a/b; mod.rs,
    lib.rs and main.rs have their own directory."""
    head, name = posixpath.split(file)
    return head if name in ("mod.rs", "lib.rs", "main.rs") else posixpath.join(head, name[:-3])


def rs_target(tree, file, path):
    """The repository path a Rust path names (crate::, super::, self::, a workspace crate, or a child
    module of this file's module), or None for the standard library or an outside crate."""
    parts = path.split("::")
    if parts[0] == "crate":
        here, root = file, None
        while here:
            here = posixpath.dirname(here)
            if posixpath.join(here, "Cargo.toml").lstrip("/") in tree.files:
                root = posixpath.join(here, "src").lstrip("/")
                break
        base, parts = root, parts[1:]
    elif parts[0] in ("self", "super"):
        base = rs_module_dir(file)
        while parts and parts[0] in ("self", "super"):
            base = posixpath.dirname(base) if parts.pop(0) == "super" else base
    elif parts[0] in rs_crates(tree):
        base, parts = rs_crates(tree)[parts[0]], parts[1:]
    else:
        child = posixpath.join(rs_module_dir(file), parts[0])
        if f"{child}.rs" not in tree.files and not tree.is_dir(child):
            return None
        base = rs_module_dir(file)
    if base is None:
        return None
    for k in range(len(parts), 0, -1):
        target = posixpath.join(base, *parts[:k])
        if f"{target}.rs" in tree.files or tree.is_dir(target):
            return target
    return base


def py_exists(tree, target):
    return f"{target}.py" in tree.files or tree.is_dir(target)


def local_target(tree, file, lang, module, package_path="", core=()):
    """The repository path an import names, or None for a library or the standard library.

    A Python import resolves from the importing file (relative), or from the package's own
    directory, its src/, the repository root or src/; `from a import b` names a/b when that
    exists, else a."""
    here = posixpath.dirname(file)
    if lang == "rs":
        return rs_target(tree, file, module)
    if lang == "cs":
        # A namespace (or, for `using X = A.B.C;`, the namespace of a type) declared in the repository:
        # outward when only files outside the core declare it. Returns one of those files.
        parts = module.split(".")
        for k in range(len(parts), 0, -1):
            files = cs_namespaces(tree).get(".".join(parts[:k]))
            if files:
                return None if any(inside(f, core) for f in files) else files[0]
        return None
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
    parts = [p for p in module[dots:].split(".") if p]
    if dots:
        base = here
        for _ in range(dots - 1):
            base = posixpath.dirname(base)
        for k in range(len(parts), 0, -1):
            target = posixpath.normpath(posixpath.join(base, *parts[:k]))
            if py_exists(tree, target):
                return target
        return posixpath.normpath(base)
    package_path = package_path.strip("/").strip(".")
    roots = [f"{package_path}/", f"{package_path}/src/"] if package_path else []
    for root in roots + ["", "src/"]:
        for k in range(len(parts), 0, -1):
            target = root + "/".join(parts[:k])
            if py_exists(tree, target):
                return target
    return None


def bare(path):
    return re.sub(r"\.(?:py|go|cs|rs|[cm]?[jt]sx?)$", "", path)


def inside(path, roots):
    """Whether path (a file, a directory, or a module path with or without its extension) is in a root."""
    return any(bare(path) == bare(root) or path.startswith(root.rstrip("/") + "/") for root in roots)


def scan_file(tree, file, core, package_path=""):
    lang = CODE[os.path.splitext(file)[1]]
    text = tree.read(file) or ""
    stripped = code_only(text, lang)
    out = []
    for line, module in imports(text, lang):
        name = module[5:] if lang == "js" and module.startswith("node:") else module
        top = name.split(".")[0] if lang == "py" else name.split("/")[0] if lang == "js" else name
        if lang in IO_SCOPES:
            sep = "." if lang == "cs" else "::"
            io = any(name == p or name.startswith(p + sep) for p in IO_SCOPES[lang])
        else:
            io = name in IO_MODULES[lang] or top in IO_MODULES[lang] or name.startswith(IO_PREFIXES[lang])
        if io:
            out.append((file, line, "io-import", f"imports {module}, an I/O module; move the call to the shell"))
            continue
        target = local_target(tree, file, lang, module, package_path, core)
        if target and not NON_CODE.search(target) and not inside(target, core):
            out.append((file, line, "outward-import",
                        f"imports {target}, outside the core; dependencies point inward, so pass its result in"))
    effects = py_effects(text) if lang == "py" else []
    if effects is None:  # Python that does not parse: read the patterns as text
        effects = [(stripped.count("\n", 0, m.start()) + 1, f"calls {m.group(0).strip()}; side effects belong in the shell")
                   for m in re.finditer(SIDE_EFFECTS[lang] + "|" + PY_CLOCK_TEXT, stripped)]
    elif lang != "py":
        effects = [(stripped.count("\n", 0, m.start()) + 1, f"calls {m.group(0).strip()}; side effects belong in the shell")
                   for m in re.finditer(SIDE_EFFECTS[lang], stripped)]
    out += [(file, line, "side-effect", what) for line, what in effects]
    return out


def scan_core(tree, package):
    """(violations, problems) for one package's core paths."""
    core = [posixpath.normpath(c.strip("/")) for c in package.get("core") or []]
    violations, problems = [], []
    if not core:
        problems.append("no core paths: list the pure domain code under \"core\"")
    for root in core:
        files = [f for f in tree.under(root) if os.path.splitext(f)[1] in CODE and not TEST_FILE.search(f)]
        if not files:
            problems.append(f"core path {root} holds no source files: the check would pass on nothing")
        for file in files:
            violations += scan_file(tree, file, core, package.get("path", ""))
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
        if not isinstance(p, dict) or not isinstance(p.get("name"), str) or not isinstance(p.get("path"), str):
            raise SystemExit(f"{where}: each package needs \"name\" and \"path\"")
        if not re.fullmatch(r"[A-Za-z0-9@_][A-Za-z0-9@._/-]*", p["name"]) or ".." in p["name"]:
            raise SystemExit(f"{where}: package name {p['name']!r}: letters, digits and @ . _ / - only, no '..'")
        if p.get("mode", "enforce") not in ("enforce", "observe"):
            raise SystemExit(f"{where}: {p['name']}: \"mode\" is \"enforce\" or \"observe\"")
        out[p["name"]] = p
    return out, list(data.get("ignore") or [])


def judges(repo, base, head=None):
    """(packages, ignore globs, notes, new names, forced names) for a change from base to head.

    verify.json at base judges: a change cannot weaken its own judge. A package new at head is
    judged by its own definition. A package whose definition the change edits keeps its base
    definition, except that enforce at head wins over observe at base, so tightening takes
    effect at once. New and edited packages are forced: they run and need evidence even when
    none of their files changed. Without head, head is the worktree.
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
    head, head_ignore = parse_manifest(head_text, f"{MANIFEST} at head") if head_text else ({}, [])
    if base_text is None:
        notes = [f"{MANIFEST} is new in this change: every package runs, judged by its own definition"] if base else []
        return head, head_ignore, notes, set(head) if base else set(), set(head) if base else set()
    packages, ignore = parse_manifest(base_text, f"{MANIFEST} at {base}")
    notes, new, forced = [], set(), set()
    if head_text is None:
        notes.append(f"this change deletes {MANIFEST}; the definitions at base still judge it")
    for name, p in head.items():
        if name not in packages:
            packages[name] = p
            new.add(name)
            forced.add(name)
            notes.append(f"{name}: new package, defined by this change; the reviewer reads its definition")
        elif fingerprint(p) != fingerprint(packages[name]):
            forced.add(name)
            if p.get("mode", "enforce") == "enforce" and packages[name].get("mode", "enforce") == "observe":
                packages[name] = {**packages[name], "mode": "enforce"}
            notes.append(f"{name}: this change edits its definition; {MANIFEST} at base judges it"
                         f"{' (in enforce mode, as head sets)' if packages[name].get('mode') == 'enforce' else ''}")
    for name in packages.keys() - head.keys() if head_text else ():
        notes.append(f"{name}: this change removes the package; {MANIFEST} at base still judges its files")
    return packages, ignore, notes, new, forced


def slug(name):
    """A file name for a package's evidence: scoped names such as @acme/web keep one file."""
    return name.replace("/", "__")


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


def changed(repo, base, head, packages, ignore, new=(), forced=()):
    """({package names changed}, [files outside every package and not ignored]).

    Renames count as a deletion and an addition, so a move changes both packages. Forced
    packages (new or with an edited definition) count as changed.
    """
    names, outside = set(forced), []
    for path in (git(repo, "diff", "--name-only", "--no-renames", f"{base}...{head}") or "").splitlines():
        if path == MANIFEST:
            continue  # judges() forces each package whose definition it adds or edits
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
    if not head or args.base and not rev_commit(args.repo, args.base):
        print(f"cannot resolve HEAD or --base {args.base}: not run")
        return 1
    if git(args.repo, "status", "--porcelain", "--untracked-files=no"):
        print("uncommitted changes: commit first, so the evidence binds to a commit")
        return 1
    packages, ignore, notes, new, forced = judges(args.repo, args.base)
    for note in notes:
        print(f"note: {note}")
    names = args.package or (sorted(changed(args.repo, args.base, head, packages, ignore, new, forced)[0]) if args.base
                             else list(packages))
    directory = out_dir(args.repo, args.out)
    os.makedirs(directory, exist_ok=True)
    failed = False
    for name in names:
        if name not in packages:
            raise SystemExit(f"no package {name!r} in {MANIFEST}")
        p = packages[name]
        log_path = os.path.join(directory, f"{slug(name)}.log")
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
        with open(os.path.join(directory, f"{slug(name)}.json"), "w", encoding="utf-8") as handle:
            json.dump(evidence, handle, indent=2)
        print(f"{name}: {'passed' if passed else 'failed'} on {head[:12]}; evidence {os.path.join(directory, slug(name))}.json")
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
    packages, ignore, notes, new, forced = judges(args.repo, base, head)
    for note in notes:
        print(f"note: {note}")
    names, outside = changed(args.repo, base, head, packages, ignore, new, forced)
    problems = [f"{path}: changed, but outside every package and not under \"ignore\"" for path in outside]
    directory = out_dir(args.repo, args.out)
    tree = Tree(args.repo, head)
    for name in sorted(names):
        p = packages[name]
        try:
            with open(os.path.join(directory, f"{slug(name)}.json"), encoding="utf-8") as handle:
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
