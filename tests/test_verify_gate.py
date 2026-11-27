"""Tests for skills/delivering/scripts/verify_gate.py: the pure-core scan and the evidence gate.

Run: python3 -m unittest tests.test_verify_gate -v
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "skills" / "delivering" / "scripts" / "verify_gate.py"
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": os.devnull,
       "GIT_CONFIG_NOSYSTEM": "1"}

MANIFEST = {
    "packages": [
        {"name": "app", "path": "app", "checks": ["python3 -c 'print(1)'"], "core": ["app/core"],
         "e2e": "python3 -m app.e2e"},
        {"name": "web", "path": "web", "core": ["web/src/core"], "e2e": "true"},
    ],
    "ignore": ["*.md"],
}
FILES = {
    "app/core/price.py": "def total(items):\n    return sum(items)\n",
    "app/shell/db.py": "import sqlite3\n\ndef save(x):\n    sqlite3.connect(':memory:')\n",
    "app/e2e.py": "import sys\nfrom app.core.price import total\nsys.exit(0 if total([1, 2]) == 3 else 1)\n",
    "app/__init__.py": "", "app/core/__init__.py": "",
    "web/src/core/cart.ts": "import { fmt } from './fmt'\nexport const sum = (a: number[]) => fmt(a.length)\n",
    "web/src/core/fmt.ts": "export const fmt = (n: number) => `${n}`\n",
    "README.md": "demo\n",
}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), "-c", "commit.gpgsign=false", *args], env=ENV, capture_output=True, text=True, check=True).stdout


def gate(repo, *args):
    run = subprocess.run([sys.executable, str(GATE), *args, "--repo", str(repo)], env=ENV,
                         capture_output=True, text=True, timeout=120)
    return run.returncode, run.stdout + run.stderr


class Gate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        self.write({**FILES, "verify.json": json.dumps(MANIFEST, indent=2)})
        self.base = self.commit("base")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, files):
        for path, text in files.items():
            target = self.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text)

    def commit(self, message):
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", message)
        return git(self.repo, "rev-parse", "HEAD").strip()

    def assertGate(self, args, code, *needles):
        result, out = gate(self.repo, *args)
        self.assertEqual(result, code, out)
        for needle in needles:
            self.assertIn(needle, out)
        return out


class Core(Gate):
    def test_clean_core_passes(self):
        self.assertGate(["core"], 0, "app: core pass", "web: core pass")

    def test_io_side_effects_and_outward_imports_fail(self):
        self.write({
            "app/core/price.py": "import os\nfrom app.shell import db\nfrom datetime import datetime\n\n"
                                 "def total(items):\n    print(items)\n    return datetime.now()\n",
            "web/src/core/cart.ts": "import { readFileSync } from 'node:fs'\nimport { save } from '../shell/db'\n"
                                    "export const sum = () => fetch('/x')\n",
        })
        out = self.assertGate(["core"], 1, "app/core/price.py:1: io-import", "app/core/price.py:2: outward-import",
                              "app/core/price.py:6: side-effect: calls print(", "app/core/price.py:7: side-effect",
                              "web/src/core/cart.ts:1: io-import", "web/src/core/cart.ts:2: outward-import",
                              "web/src/core/cart.ts:3: side-effect: calls fetch(")
        self.assertNotIn("datetime, an I/O module", out)

    def test_python_clock_and_randomness_calls_resolve_through_imports(self):
        cases = {  # file: (source, the clock call's line or None for pure code)
            "named.py": ("from time import time\n\ndef f():\n    return time()\n", 4),
            "alias.py": ("import time as t\n\ndef f():\n    return t.time()\n", 4),
            "chain.py": ("import datetime\n\ndef f():\n    return datetime.datetime.now()\n", 4),
            "pick.py": ("from random import choice as pick\n\ndef f(xs):\n    return pick(xs)\n", 4),
            "local.py": ("import time\n\ndef total():\n    return time.time()\n\n"
                         "def pure():\n    import math as time\n    return time.sqrt(4)\n", 4),
            "siblings.py": ("def a():\n    from math import sin as now\n    return now(0)\n\n"
                            "def b():\n    from time import time as now\n    return now()\n", 7),
            "shadow.py": ("from math import sin as now\n\ndef f():\n    from time import time as now\n    return now()\n", 5),
            "nested.py": ("def a():\n    from time import time as now\n    return 1\n\n"
                          "def now():\n    return 0\n\nx = now()\n", None),
            "later.py": ("import math as t\nimport time as t\n\ndef f():\n    return t.time()\n", 5),
            "later_pure.py": ("import time as t\nimport math as t\n\ndef f():\n    return t.sqrt(4)\n", None),
            "rebound_pure.py": ("from time import time as fn\nfrom math import sin as fn\n\ndef f():\n    return fn(0)\n", None),
            "between.py": ("def f():\n    from time import time as now\n    x = now()\n"
                           "    from math import sin as now\n    return x\n", 3),
            "local_rebound.py": ("def f():\n    from time import time as now\n    from math import sin as now\n    return now(0)\n", None),
            "maybe.py": ("from math import sin as now\ntry:\n    from time import time as now\nexcept ImportError:\n    pass\n\n"
                         "def f():\n    return now()\n", 8),
            "class_hidden.py": ("from time import time as now\n\nclass C:\n    from math import sin as now\n\nstamp = now()\n", 6),
            "async_hidden.py": ("from time import time as now\n\nasync def g():\n    from math import sin as now\n\nstamp = now()\n", 6),
            "class.py": ("class C:\n    from time import time as now\n    stamp = now()\n", 3),
            "async.py": ("async def f():\n    from time import time as now\n    return now()\n", 3),
            "block.py": ("if True:\n    import time as t\n\ndef f():\n    return t.time()\n", 5),
            "pure.py": ("import time as t\nimport uuid as u\nimport datetime as d\nfrom datetime import datetime as dt\n"
                        "from uuid import UUID\nfrom random import Random\n\n"
                        "def f():\n    return (t.gmtime(0), u.UUID(int=0), UUID(int=1), d.timedelta(seconds=2),"
                        " dt(2000, 1, 2), d.datetime(2000, 1, 2), Random(1).random())\n", None),
        }
        for name, (source, line) in cases.items():
            with self.subTest(name=name):
                self.write({"app/core/price.py": source})
                if line:
                    out = self.assertGate(["core"], 1, f"price.py:{line}: side-effect: calls")
                    self.assertEqual(out.count("side-effect"), 1, out)
                else:
                    self.assertGate(["core"], 0, "app: core pass")

    def test_go_core_imports(self):
        self.write({"go.mod": "module example.com/m\n\ngo 1.22\n",
                    "svc/domain/rule.go": 'package domain\n\nimport (\n\t"strings"\n\t"os"\n\n'
                                          '\t"example.com/m/svc/domain/money"\n\t"example.com/m/svc/store"\n)\n\n'
                                          'func Rule() string { return strings.ToUpper(os.Getenv("X")) + time.Now().String() }\n',
                    "svc/domain/money/money.go": "package money\n",
                    "verify.json": json.dumps({"packages": [{"name": "svc", "path": "svc", "core": ["svc/domain"],
                                                             "e2e": "true"}]})})
        out = self.assertGate(["core"], 1, "svc/domain/rule.go:5: io-import: imports os",
                              "svc/domain/rule.go:8: outward-import: imports svc/store",
                              "svc/domain/rule.go:11: side-effect: calls time.Now(")
        self.assertNotIn("svc/domain/money,", out)
        self.assertNotIn("strings", out)

    def test_comments_strings_and_tests_are_not_code(self):
        self.write({"app/core/price.py": '"""Never print( here."""\n# import os\n\ndef total(items):\n'
                                         '    return "fetch(" + str(sum(items))  # print(x)\n',
                    "app/core/test_price.py": "import os\nprint(os.getcwd())\n",
                    "web/src/core/cart.test.ts": "import fs from 'fs'\nconsole.log(fs)\n"})
        self.assertGate(["core"], 0, "app: core pass", "web: core pass")

    def test_imports_in_js_and_go_comments_or_strings_are_not_imports(self):
        self.write({"web/src/core/cart.ts": "// import fs from 'fs'\n/* require('child_process') */\n"
                                            "export const doc = \"import { x } from 'node:fs'\"\n",
                    "go.mod": "module example.com/m\n",
                    "svc/domain/rule.go": 'package domain\n\n/*\nimport "os"\n*/\nconst doc = `\nimport "net/http"\n`\n',
                    "verify.json": json.dumps({"packages": MANIFEST["packages"] + [
                        {"name": "svc", "path": "svc", "core": ["svc/domain"], "e2e": "true"}]})})
        self.assertGate(["core"], 0, "web: core pass", "svc: core pass")

    def test_aliased_python_imports_and_one_line_go_groups_are_read(self):
        self.write({"app/core/price.py": "import math as m, os\n\ndef total(items):\n    return m.fsum(items)\n",
                    "go.mod": "module example.com/m\n",
                    "svc/domain/rule.go": 'package domain\n\nimport ("os")\n\nfunc X() string { return os.Getenv("X") }\n',
                    "verify.json": json.dumps({"packages": MANIFEST["packages"] + [
                        {"name": "svc", "path": "svc", "core": ["svc/domain"], "e2e": "true"}]})})
        self.assertGate(["core"], 1, "app/core/price.py:1: io-import: imports os", "svc/domain/rule.go:3: io-import: imports os")

    def test_template_literal_expressions_are_code(self):
        self.write({"web/src/core/cart.ts": "export const v = `total: ${fetch('/x')}`\nexport const w = `fetch(` + 'console.log'\n"})
        out = self.assertGate(["core"], 1, "web/src/core/cart.ts:1: side-effect: calls fetch(")
        self.assertNotIn("cart.ts:2", out)

    def test_template_escapes_strings_and_comments(self):
        self.write({"web/src/core/cart.ts": 'export const a = `\\${fetch("/x")}`\n'
                                            'export const b = `${"}" + fetch("/y")}`\n'
                                            'export const c = `${/* } */ fetch("/z")}`\n'})
        out = self.assertGate(["core"], 1, "cart.ts:2: side-effect: calls fetch(", "cart.ts:3: side-effect: calls fetch(")
        self.assertNotIn("cart.ts:1", out)

    def test_monorepo_python_imports_resolve_from_the_package_root(self):
        manifest = {"packages": [{"name": "billing", "path": "services/billing", "core": ["services/billing/billing/core"],
                                  "e2e": "true"}]}
        for source, line in (("from billing.shell import db\n", 1), ("from billing import shell\n", 1),
                             ("from billing import core\nfrom billing.core import rules\n", None),
                             ("from .. import shell\n", 1), ("from . import rules\n", None)):
            with self.subTest(source=source):
                self.write({"verify.json": json.dumps(manifest),
                            "services/billing/billing/__init__.py": "", "services/billing/billing/shell/__init__.py": "",
                            "services/billing/billing/core/__init__.py": "", "services/billing/billing/core/rules.py": "X = 1\n",
                            "services/billing/billing/core/total.py": source})
                if line:
                    self.assertGate(["core"], 1, f"core/total.py:{line}: outward-import")
                else:
                    self.assertGate(["core"], 0, "billing: core pass")

    def test_file_listed_cores_and_extensionful_imports(self):
        manifest = {"packages": [{"name": "web", "path": "web", "core": ["web/src/cart.ts", "web/src/fmt.ts"], "e2e": "true"}]}
        self.write({"verify.json": json.dumps(manifest), "web/src/fmt.ts": "export const fmt = (n: number) => `${n}`\n",
                    "web/src/db.ts": "export const db = 1\n",
                    "web/src/cart.ts": "import { fmt } from './fmt.js'\nimport { db } from './db.js'\n"})
        out = self.assertGate(["core"], 1, "web/src/cart.ts:2: outward-import")
        self.assertNotIn("cart.ts:1", out)

    def test_go_raw_strings_and_js_nested_templates_and_regexes(self):
        self.write({"go.mod": "module example.com/m\n",
                    "svc/domain/rule.go": "package domain\n\nconst sep = `\\`\nconst doc = `time.Now()`\n"
                                          "func f() { _ = time.Now() }\nconst end = `x`\n",
                    "web/src/core/cart.ts": "export const a = `${ ok ? `label` : fetch('/real') }`;\n"
                                            "export const b = `${ ok ? `fetch('/fake')` : 'none' }`;\n"
                                            "export const c = s.replace(/\"/g, \"\") + fetch(\"/x\")\n"
                                            "export const d = n++ / fetch('/y')\n"
                                            "if (s) /console.log/.test(s)\n"
                                            "export const e = /[/]fetch(/.test(s)\n",
                    "verify.json": json.dumps({"packages": MANIFEST["packages"] + [
                        {"name": "svc", "path": "svc", "core": ["svc/domain"], "e2e": "true"}]})})
        out = self.assertGate(["core"], 1, "rule.go:5: side-effect", "cart.ts:1: side-effect: calls fetch(",
                              "cart.ts:3: side-effect: calls fetch(", "cart.ts:4: side-effect: calls fetch(")
        for line in (2, 5, 6):
            self.assertNotIn(f"cart.ts:{line}", out)
        self.assertNotIn("rule.go:4", out)

    def test_python_builtins_in_f_strings_and_scopes(self):
        cases = {
            "fstring.py": ('def f(p):\n    return f"{open(p).read()}"\n', 2),
            "class_scope.py": ("class C:\n    from builtins import len as open\n    n = open('ab')\n\n"
                               "    def m(self, p):\n        return open(p)\n", 6),
            "rebind.py": ("def f(p):\n    x = open(p)\n    open = len\n    return x\n", 2),
            "imported.py": ("from builtins import len as open\n\ndef f(p):\n    return open(p)\n", None),
            "builtin_import.py": ("from builtins import open\n\ndef f(p):\n    return open(p).read()\n", 4),
            "builtins_module.py": ("import builtins\n\ndef f(x):\n    builtins.print(x)\n", 4),
        }
        for name, (source, line) in cases.items():
            with self.subTest(name=name):
                self.write({"app/core/price.py": source})
                if line:
                    out = self.assertGate(["core"], 1, f"price.py:{line}: side-effect: calls ")
                    self.assertEqual(out.count("side-effect"), 1, out)
                else:
                    self.assertGate(["core"], 0, "app: core pass")

    def test_file_listed_python_core_and_dotted_core_roots(self):
        manifest = {"packages": [{"name": "app", "path": "app", "core": ["./app/core/price.py", "app/core/rule.py"],
                                  "e2e": "true"}]}
        self.write({"verify.json": json.dumps(manifest), "app/core/rule.py": "X = 1\n",
                    "app/core/price.py": "from . import rule\nfrom ..shell import db\nfrom .. import settings\n"})
        out = self.assertGate(["core"], 1, "app/core/price.py:2: outward-import", "app/core/price.py:3: outward-import")
        self.assertNotIn("price.py:1", out)
        self.assertNotIn("holds no source files", out)

    def test_bad_package_names_are_refused(self):
        for name in ("bad name", "app/../x", "/abs"):
            with self.subTest(name=name):
                self.write({"verify.json": json.dumps({"packages": [{"name": name, "path": "app", "core": ["app/core"],
                                                                    "e2e": "true"}]})})
                self.assertGate(["core"], 1, "package name")

    def test_scoped_io_packages_are_io(self):
        self.write({"web/src/core/cart.ts": "import { S3Client } from '@aws-sdk/client-s3'\nexport const s = S3Client\n"})
        self.assertGate(["core"], 1, "web/src/core/cart.ts:1: io-import")

    def test_observe_mode_reports_without_failing(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"][0]["mode"] = "observe"
        self.write({"verify.json": json.dumps(manifest), "app/core/price.py": "import socket\n"})
        self.assertGate(["core"], 0, "observe: app: app/core/price.py:1: io-import")

    def test_empty_core_fails(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"][1]["core"] = ["web/src/missing"]
        self.write({"verify.json": json.dumps(manifest)})
        self.assertGate(["core"], 1, "web: core path web/src/missing holds no source files")


class Evidence(Gate):
    def change_app(self, body="def total(items):\n    return sum(items, 0)\n"):
        self.write({"app/core/price.py": body})
        return self.commit("change app")

    def test_passing_run_then_check_covers_only_changed_packages(self):
        head = self.change_app()
        out = self.assertGate(["run", "--base", self.base], 0, "app: e2e: python3 -m app.e2e: exit 0")
        self.assertNotIn("web:", out)
        self.assertGate(["check", "--base", self.base], 0, f"app: pass", head[:12])

    def test_without_evidence_check_fails(self):
        self.change_app()
        self.assertGate(["check", "--base", self.base], 1, "app: no evidence")

    def test_failing_e2e_fails(self):
        self.change_app("def total(items):\n    return 0\n")
        self.assertGate(["run", "--base", self.base], 1, "app: e2e: python3 -m app.e2e: exit 1")
        self.assertGate(["check", "--base", self.base], 1, "app: no passing e2e step")

    def test_new_commit_makes_evidence_stale(self):
        self.change_app()
        self.assertGate(["run", "--base", self.base], 0)
        self.change_app("def total(items):\n    return sum(list(items))\n")
        self.assertGate(["check", "--base", self.base], 1, "evidence is for")

    def test_core_violation_fails_run_and_check(self):
        self.change_app("import requests\n\ndef total(items):\n    return sum(items)\n")
        self.assertGate(["run", "--base", self.base], 1, "app: core: core: exit 1")
        self.assertGate(["check", "--base", self.base], 1, "app/core/price.py:1: io-import")

    def test_a_change_cannot_weaken_its_own_judge(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"][0]["e2e"] = "true"
        self.write({"verify.json": json.dumps(manifest), "app/core/price.py": "def total(items):\n    return 0\n"})
        self.commit("weaken e2e and break total")
        self.assertGate(["run"], 0)  # head's weaker definition passes
        out = self.assertGate(["check", "--base", self.base], 1, "verify.json at base judges it",
                              "app: evidence ran another definition")
        self.assertNotIn("verify.json: changed", out)
        self.assertGate(["run", "--base", self.base], 1, "app: e2e: python3 -m app.e2e: exit 1")

    def test_a_move_between_packages_changes_both(self):
        git(self.repo, "mv", "app/shell/db.py", "web/db.py")
        self.commit("move db")
        out = self.assertGate(["run", "--base", self.base], 0, "app: e2e", "web: e2e")
        self.assertGate(["check", "--base", self.base], 0, "app: pass", "web: pass")

    def test_a_new_nested_package_cannot_take_files_from_their_judge(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"].append({"name": "new-core", "path": "app/core", "core": ["app/core"], "e2e": "true"})
        self.write({"verify.json": json.dumps(manifest), "app/core/price.py": "def total(items):\n    return 0\n"})
        self.commit("nested package and a broken total")
        self.assertGate(["run", "--base", self.base], 1, "app: check", "app: e2e: python3 -m app.e2e: exit 1")
        self.assertGate(["check", "--base", self.base], 1, "app: no passing e2e step")

    def test_a_new_nested_package_is_judged_too(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"].append({"name": "addon", "path": "app/addon", "core": ["app/addon"], "e2e": "false"})
        self.write({"verify.json": json.dumps(manifest), "app/addon/x.py": "X = 1\n"})
        self.commit("new nested package with a failing e2e")
        self.assertGate(["run", "--base", self.base], 1, "app: passed", "addon: e2e: false: exit 1")
        self.assertGate(["check", "--base", self.base], 1, "addon: no passing e2e step")

    def test_the_deepest_base_package_owns_a_file(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"].append({"name": "pricing", "path": "app/core", "core": ["app/core"], "e2e": "true"})
        self.write({"verify.json": json.dumps(manifest)})
        base = self.commit("nested package at base")
        self.write({"app/core/price.py": "def total(items):\n    return sum(items, 0)\n"})
        self.commit("change pricing")
        out = self.assertGate(["run", "--base", base], 0, "pricing: passed")
        self.assertNotIn("app: ", out)

    def test_a_step_that_rewrites_tracked_code_fails(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"][0]["checks"] = ["printf 'def total(items):\\n    return 3\\n' > app/core/price.py"]
        self.write({"verify.json": json.dumps(manifest)})
        base = self.commit("a check that edits code")
        self.write({"app/core/price.py": "def total(items):\n    return 0\n"})
        self.commit("break total")
        self.assertGate(["run", "--base", base], 1, "changed HEAD or tracked files")
        git(self.repo, "checkout", "-q", "--", ".")
        self.assertGate(["check", "--base", base], 1, "app: no passing e2e step")

    def test_changed_file_outside_every_package_fails_unless_ignored(self):
        self.write({"tools/x.py": "x = 1\n", "NOTES.md": "n\n"})
        self.commit("outside")
        out = self.assertGate(["check", "--base", self.base], 1, "tools/x.py: changed, but outside every package")
        self.assertNotIn("NOTES.md", out)

    def test_the_first_verify_json_judges_every_package(self):
        git(self.repo, "rm", "-q", "verify.json")
        base = self.commit("no manifest yet")
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"][1]["e2e"] = "false"
        self.write({"verify.json": json.dumps(manifest)})
        self.commit("add verify.json")
        self.assertGate(["run", "--base", base], 1, "verify.json is new", "app: passed", "web: e2e: false: exit 1")
        self.assertGate(["check", "--base", base], 1, "web: no passing e2e step")

    def test_a_package_added_alone_runs_and_needs_evidence(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"].append({"name": "@acme/docs", "path": "docs", "core": ["web/src/core"], "e2e": "false"})
        self.write({"verify.json": json.dumps(manifest)})
        self.commit("add a package and nothing else")
        out = self.assertGate(["run", "--base", self.base], 1, "@acme/docs: e2e: false: exit 1")
        self.assertNotIn("app: e2e", out)
        self.assertGate(["check", "--base", self.base], 1, "@acme/docs: no passing e2e step")
        self.assertEqual(sorted(p.name for p in Path(git(self.repo, "rev-parse", "--absolute-git-dir").strip(), "verify")
                                .glob("*.json")), ["@acme__docs.json"])

    def test_an_edited_definition_runs_its_package(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"][1]["checks"] = ["true"]
        self.write({"verify.json": json.dumps(manifest)})
        self.commit("edit web's definition only")
        self.assertGate(["run", "--base", self.base], 0, "web: e2e: true: exit 0")
        self.assertGate(["check", "--base", self.base], 0, "web: pass")

    def test_observe_to_enforce_takes_effect_at_once(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"][0]["mode"] = "observe"
        self.write({"verify.json": json.dumps(manifest)})
        base = self.commit("observe at base")
        manifest["packages"][0]["mode"] = "enforce"
        self.write({"verify.json": json.dumps(manifest), "app/core/price.py": "import socket\n"})
        self.commit("enforce, with an I/O import")
        self.assertGate(["run", "--base", base], 1, "app: core: core: exit 1")
        self.assertGate(["check", "--base", base], 1, "app/core/price.py:1: io-import")

    def test_observe_package_passes_run_and_check_despite_violations(self):
        manifest = json.loads(json.dumps(MANIFEST))
        manifest["packages"][0]["mode"] = "observe"
        self.write({"verify.json": json.dumps(manifest)})
        base = self.commit("observe at base")
        self.write({"app/core/price.py": "import socket\n\ndef total(items):\n    return sum(items)\n"})
        self.commit("I/O in an observed core")
        self.assertGate(["run", "--base", base], 0, "app: core: core: exit 0")
        self.assertGate(["check", "--base", base], 0, "observe: app: app/core/price.py:1: io-import", "app: pass")

    def test_forged_evidence_does_not_hide_a_core_violation(self):
        self.write({"app/core/price.py": "def total(items):\n    return sum(items, 0)\n"})
        self.commit("clean")
        self.assertGate(["run", "--base", self.base], 0)
        evidence = Path(git(self.repo, "rev-parse", "--absolute-git-dir").strip(), "verify", "app.json")
        record = json.loads(evidence.read_text())
        self.write({"app/core/price.py": "import requests\n\ndef total(items):\n    return sum(items)\n"})
        record["head"] = self.commit("I/O after the run")
        evidence.write_text(json.dumps(record))
        self.assertGate(["check", "--base", self.base], 1, "app/core/price.py:1: io-import")

    def test_removing_a_package_or_the_manifest_is_noted_and_judged_by_base(self):
        manifest = json.loads(json.dumps(MANIFEST))
        del manifest["packages"][1]
        self.write({"verify.json": json.dumps(manifest), "web/src/core/fmt.ts": "export const fmt = 1\n"})
        self.commit("drop web and change it")
        self.assertGate(["check", "--base", self.base], 1, "web: this change removes the package", "web: no evidence")
        git(self.repo, "rm", "-q", "verify.json")
        self.commit("drop the manifest")
        self.assertGate(["check", "--base", self.base], 1, "this change deletes verify.json", "web: no evidence")

    def test_bad_base_is_refused(self):
        for command in ("run", "check"):
            with self.subTest(command=command):
                self.assertGate([command, "--base", "no-such-rev"], 1, "cannot resolve")

    def test_run_refuses_uncommitted_changes(self):
        self.write({"app/core/price.py": "def total(items):\n    return 1\n"})
        self.assertGate(["run"], 1, "uncommitted changes")

    def test_help(self):
        self.assertEqual(subprocess.run([sys.executable, str(GATE), "--help"], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
