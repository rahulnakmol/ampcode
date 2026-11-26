#!/usr/bin/env python3
"""Run `sync.py azure|linear plan` against an in-memory fake tracker. No network, no token.

  python3 tests/fixtures/syncing/fake_plan.py azure  [backlog.json]
  python3 tests/fixtures/syncing/fake_plan.py linear [backlog.json]

The fake starts empty (organisation acme, project close; or team FIN, project "Month-end close"),
so the plan creates everything. Without backlog.json it uses the grooming skill's operations
example and the planning worked example's PRD. The fakes are those in tests/test_syncing.py.
This is the W17 and W18 human test: read the plan, its target line, and its digest.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tests"))
import test_syncing as fakes  # noqa: E402

ARGS = {"azure": ["--org", "acme", "--project", "close"], "linear": ["--team", "FIN", "--project", "Month-end close"]}


def main(argv):
    if not argv or argv[0] not in ARGS or len(argv) > 2:
        print(__doc__)
        return 0 if argv[:1] in (["-h"], ["--help"]) else 2
    tracker = argv[0]
    with tempfile.TemporaryDirectory() as tmp:
        if len(argv) == 2:
            path = Path(argv[1]).resolve()
        else:
            shutil.copy(ROOT / "skills/planning/reference/worked-example/prd.md", Path(tmp, "prd.md"))
            path = Path(tmp, "backlog.json")
            path.write_text(json.dumps(fakes.example()))
        module, fake = (fakes.azure, fakes.FakeAzure()) if tracker == "azure" else (fakes.linear, fakes.FakeLinear())
        code, out, err = fakes.run_main([tracker, "plan", str(path), *ARGS[tracker]], module, fake.call)
        print(out + err, end="")
        return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
