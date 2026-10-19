"""Keeps the distilling-videos skill guidance executable.

Run: python3 -m unittest discover -s tests -p 'test_distilling_skill_docs.py' -v
Every JSON block preceded by `<!-- example: NAME -->` in SKILL.md or reference/*.md is run through
the real CLI, so documented examples cannot drift from the contracts. No network or paid calls.
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "distilling-videos"
SCRIPTS = SKILL / "scripts"
DISTILL = SCRIPTS / "distill.py"
sys.path.insert(0, str(SCRIPTS))

import evidence  # noqa: E402

EXAMPLE = re.compile(r"<!-- example: ([a-z0-9-]+) -->\n```json\n(.*?)\n```", re.S)


def examples():
    found = {}
    for path in [SKILL / "SKILL.md", *sorted((SKILL / "reference").glob("*.md"))]:
        for name, body in EXAMPLE.findall(path.read_text()):
            if name in found:
                raise AssertionError(f"duplicate example {name}")
            found[name] = json.loads(body)
    return found


class SkillDocs(unittest.TestCase):
    def test_skill_md_is_short_and_has_metadata(self):
        text = (SKILL / "SKILL.md").read_text()
        self.assertLess(len(text.splitlines()), 500)
        self.assertRegex(text, r"\A---\nname: distilling-videos\ndescription: \"[^\n]+\"\n---\n")

    def test_documented_cli_flags_exist(self):
        help_text = {}
        text = (SKILL / "SKILL.md").read_text() + (SKILL / "reference" / "providers.md").read_text() \
            + (SKILL / "reference" / "evaluations.md").read_text()
        for command, flags in re.findall(r"\$D ((?:budget )?[a-z-]+)((?:\\\n|[^\n])*)", text):
            if command not in help_text:
                result = subprocess.run([sys.executable, str(DISTILL), *command.split(), "--help"],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, f"{command}: {result.stderr}")
                help_text[command] = result.stdout
            for flag in re.findall(r"(?<![\w-])(--[a-z][a-z-]*)", flags):
                self.assertRegex(help_text[command], re.escape(flag) + r"(?![\w-])", f"{command} has no {flag}")

    def test_examples_validate_through_the_cli(self):
        found = examples()
        for name in ("assignment", "transcript-en", "transcript-ja", "article", "review"):
            self.assertIn(name, found)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ws = root / "ws"

            def cli(*args):
                return subprocess.run([sys.executable, str(DISTILL), *map(str, args)], capture_output=True,
                                      text=True, env={"PATH": "/usr/bin:/bin", "HOME": tmp})

            def write(name, data):
                path = root / name
                path.write_text(json.dumps(data, ensure_ascii=False))
                return path

            def ok(result):
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                return json.loads(result.stdout)

            ok(cli("init", "--workspace", ws, "--assignment", write("a.json", found["assignment"])))
            plan = json.loads((ws / "assignment.json").read_text())
            self.assertEqual([p["id"] for p in plan["publications"]], ["g-cache", "talk1", "ja-talk"])

            for name in ("transcript-en", "transcript-ja"):
                data = found[name]
                ok(cli("import-transcript", "--workspace", ws, "--video", data["video_id"],
                       "--transcript", write(f"{name}.json", data)))
            coverage = json.loads((ws / "sources/talk1/transcript/coverage.json").read_text())
            self.assertEqual(coverage["gaps"], [])
            self.assertEqual(coverage["uncertain_segment_ids"], ["s3"])

            # Frames normally come from `frames`; fabricate the documented frame without ffmpeg.
            workspace = evidence.Workspace(ws)
            base = workspace.source_dir("talk1")
            frame = "f000024000"
            for kind in ("full", "thumbs"):
                path = base / "frames" / kind / f"{frame}.jpg"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"\xff\xd8fixture")
            evidence.atomic_write_json(base / "frames" / "frames.json", {
                "schema_version": 1, "video_id": "talk1", "duration": 30.0, "max_sampling_gap_seconds": 10.0,
                "selection": {"semantic_completeness": False},
                "frames": [{"id": frame, "t": 24.0, "reasons": ["cue"], "path": f"frames/full/{frame}.jpg",
                            "thumbnail": f"frames/thumbs/{frame}.jpg"}]})
            outputs = evidence.file_digests(base, ["frames/frames.json", f"frames/full/{frame}.jpg",
                                                   f"frames/thumbs/{frame}.jpg"])
            evidence.mark_complete(workspace, evidence.stage_key("talk1", "frames"), {"fixture": 1}, {}, outputs)
            ok(cli("select-frames", "--workspace", ws, "--video", "talk1", "--frames", frame))

            (ws / "publications/talk1/article.json").write_text(json.dumps(found["article"]))
            rendered = ok(cli("render", "--workspace", ws, "--publication", "talk1"))
            self.assertEqual(rendered["status"], "rendered")
            packaged = ok(cli("package", "--workspace", ws, "--publication", "talk1", "--allow-missing-pdf"))
            self.assertFalse(packaged["complete"])

            # The review is well formed (not exit 2). It is blocked only because this fixture has no
            # download stage or PDF, which a real run supplies.
            result = cli("signoff", "--workspace", ws, "--publication", "talk1",
                         "--review", write("review.json", found["review"]))
            self.assertEqual(result.returncode, 1, result.stderr + result.stdout)
            signoff = json.loads((ws / "publications/talk1/signoff.json").read_text())
            self.assertEqual(signoff["status"], "blocked")
            for blocker in signoff["blockers"]:
                self.assertRegex(blocker, r"package is incomplete|download stage")


if __name__ == "__main__":
    unittest.main()
