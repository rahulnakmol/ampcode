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
       "GIT_COMMITTER_EMAIL": "t@t", "GIT_CONFIG_GLOBAL": os.devnull}

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
    return subprocess.run(["git", "-C", str(repo), *args], env=ENV, capture_output=True, text=True, check=True).stdout


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

    def test_python_clock_and_randomness_imported_by_name(self):
        self.write({"app/core/price.py": "from time import time, gmtime\nfrom random import choice\nfrom uuid import UUID\n\n"
                                         "def total(items):\n    return time() + choice(items)\n"})
        out = self.assertGate(["core"], 1, "price.py:1: side-effect: imports time.time", "price.py:2: side-effect: imports random.choice")
        self.assertNotIn("gmtime", out)
        self.write({"app/core/price.py": "import time as t\nimport math as m\nfrom datetime import datetime as dt, timedelta\n"})
        out = self.assertGate(["core"], 1, "price.py:1: side-effect: imports time as t", "price.py:3: side-effect: imports datetime.datetime as dt")
        self.assertNotIn("math", out)
        self.assertNotIn("timedelta", out)
        self.assertNotIn("UUID", out)

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

    def test_run_refuses_uncommitted_changes(self):
        self.write({"app/core/price.py": "def total(items):\n    return 1\n"})
        self.assertGate(["run"], 1, "uncommitted changes")

    def test_help(self):
        self.assertEqual(subprocess.run([sys.executable, str(GATE), "--help"], capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
