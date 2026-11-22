"""Anatomy rules A1 and A3 to A7 for the wave 1 and 2 skills (contract section 6).

Run: python3 -m unittest tests.test_skill_anatomy -v
Check one skill before milestone integration (skips results.md and the README rows):
    python3 tests/test_skill_anatomy.py --skill <name> --item
"""

import ast
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# The mission thread adds each skill here at milestone integration.
NEW_SKILLS = ("architecting", "interrogating-changes", "releasing")

SECTIONS = ("Common rationalizations", "Red flags", "Adapt it", "Check your work")
BANNED = (
    "budget used", "token budget", "review budget", "budget call", "merge mode", "ask mode",
    "high-risk merge", "owner merge acknowledgment",
)
LIMIT = 1024


def frontmatter(text):
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        return {}
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        fields[key.strip()] = value
    return fields


def problems(name, root=ROOT, item=False):
    """Return one 'rule: message' string per broken rule for skills/<name>."""
    out = []
    skill = root / "skills" / name
    path = skill / "SKILL.md"
    if not path.is_file():
        return [f"A1: {path.relative_to(root)} is missing"]
    text = path.read_text()
    meta = frontmatter(text)

    # A1: name, directory and description.
    words = (meta.get("name") or "").split("-")
    if meta.get("name") != name or not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name) \
            or not any(w.endswith("ing") for w in words):
        out.append(f"A1: name {meta.get('name')!r} must be a lowercase gerund equal to {name!r}")
    description = meta.get("description", "")
    if not description or len(description) > LIMIT:
        out.append(f"A1: description must be 1 to {LIMIT} characters, has {len(description)}")
    for phrase in ("Use when", "Not for"):
        if phrase not in description:
            out.append(f"A1: description must say {phrase!r}")

    # A3: required sections.
    headings = re.findall(r"^#{2,3} (.+?)\s*$", text, re.M)
    for section in SECTIONS:
        if section not in headings:
            out.append(f"A3: missing section {section!r}")

    # A4: eval scenarios, and results after integration.
    evals = root / "evals" / name
    readme = evals / "README.md"
    scenarios = re.findall(r"^\| S\d+ \|", readme.read_text(), re.M) if readme.is_file() else []
    if len(scenarios) < 2:
        out.append(f"A4: evals/{name}/README.md needs at least 2 scenario rows (| S1 | ...)")
    if not item and not (evals / "results.md").is_file():
        out.append(f"A4: evals/{name}/results.md is missing")

    # A5: routing rows, after integration.
    if not item:
        if f"skills/{name}/" not in _read(root / "README.md"):
            out.append(f"A5: README.md has no row linking skills/{name}/")
        if f"**{name}**" not in _read(root / "docs" / "using-skills.md"):
            out.append(f"A5: docs/using-skills.md has no **{name}** row")

    # A6: banned budget and merge-gate phrases anywhere in the skill.
    for file in sorted(p for p in skill.rglob("*") if p.is_file()):
        body = _read(file).lower()
        for phrase in BANNED:
            if phrase in body:
                out.append(f"A6: {file.relative_to(root)} contains {phrase!r}")

    # A7: scripts use the standard library and answer --help.
    scripts = skill / "scripts"
    local = {p.stem for p in scripts.glob("*.py")} if scripts.is_dir() else set()
    for script in sorted(scripts.glob("*.py")) if scripts.is_dir() else []:
        for module in _imports(script):
            if module not in sys.stdlib_module_names and module not in local:
                out.append(f"A7: {script.relative_to(root)} imports {module!r}, not the standard library")
        run = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, text=True, timeout=60)
        if run.returncode != 0:
            out.append(f"A7: {script.relative_to(root)} --help exits {run.returncode}")
    return out


def _read(path):
    try:
        return path.read_text()
    except (FileNotFoundError, UnicodeDecodeError):
        return ""


def _imports(script):
    tree = ast.parse(script.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module.split(".")[0]


GOOD = """---
name: sampling-things
description: "Samples things. Use when asked to sample. Not for counting."
---

# Sampling things

## Common rationalizations

## Red flags

## Adapt it

## Check your work
"""


class Rules(unittest.TestCase):
    def tree(self, tmp, skill=GOOD, script="import json\nimport sys\nif '--help' in sys.argv: print('usage')\n",
             evals="| S1 | a |\n| S2 | b |\n", results=True, rows=True):
        root = Path(tmp)
        base = root / "skills" / "sampling-things"
        (base / "scripts").mkdir(parents=True)
        (base / "SKILL.md").write_text(skill)
        (base / "scripts" / "tool.py").write_text(script)
        (root / "evals" / "sampling-things").mkdir(parents=True)
        (root / "evals" / "sampling-things" / "README.md").write_text(evals)
        if results:
            (root / "evals" / "sampling-things" / "results.md").write_text("graded\n")
        (root / "docs").mkdir()
        (root / "README.md").write_text("[x](./skills/sampling-things/SKILL.md)\n" if rows else "")
        (root / "docs" / "using-skills.md").write_text("| **sampling-things** |\n" if rows else "")
        return root

    def rules(self, item=False, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            return sorted({p.split(":")[0] for p in problems("sampling-things", self.tree(tmp, **kw), item)})

    def test_complete_skill_passes(self):
        self.assertEqual(self.rules(), [])

    def test_a1_name_and_description(self):
        self.assertEqual(self.rules(skill=GOOD.replace("name: sampling-things", "name: sampler")), ["A1"])
        self.assertEqual(self.rules(skill=GOOD.replace(" Not for counting.", "")), ["A1"])

    def test_a3_missing_section(self):
        self.assertEqual(self.rules(skill=GOOD.replace("## Red flags\n", "")), ["A3"])

    def test_a4_scenarios_and_results(self):
        self.assertEqual(self.rules(evals="| S1 | a |\n"), ["A4"])
        self.assertEqual(self.rules(results=False), ["A4"])

    def test_a5_routing_rows(self):
        self.assertEqual(self.rules(rows=False), ["A5"])

    def test_a6_banned_phrase(self):
        self.assertEqual(self.rules(skill=GOOD + "\nKeep a review budget.\n"), ["A6"])

    def test_a7_script_imports_and_help(self):
        self.assertEqual(self.rules(script="import yaml\n"), ["A7"])
        self.assertEqual(self.rules(script="import sys\nsys.exit(3)\n"), ["A7"])

    def test_item_mode_skips_results_and_rows(self):
        self.assertEqual(self.rules(item=True, results=False, rows=False), [])


class NewSkills(unittest.TestCase):
    def test_every_new_skill_meets_the_anatomy(self):
        for name in NEW_SKILLS:
            with self.subTest(skill=name):
                self.assertEqual(problems(name), [])


if __name__ == "__main__":
    if "--skill" in sys.argv:
        found = problems(sys.argv[sys.argv.index("--skill") + 1], item="--item" in sys.argv)
        print("\n".join(found) or "pass")
        sys.exit(1 if found else 0)
    unittest.main()
