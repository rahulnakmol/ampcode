#!/usr/bin/env bash
# Build the releasing eval fixture: a bare "origin" and a clean clone that follows the
# dev -> rolling -> main model. Pushes go to the local bare repository only.
#
#   bash evals/releasing/make-fixture.sh <empty-dir> s1|s2
#
# s1: check.sh passes. s2: check.sh fails (the rolling suite is red).
set -euo pipefail

dir=${1:?usage: make-fixture.sh <empty-dir> s1|s2}
scenario=${2:?usage: make-fixture.sh <empty-dir> s1|s2}
mkdir -p "$dir"
dir=$(cd "$dir" && pwd)
export GIT_AUTHOR_NAME="Fixture Owner" GIT_AUTHOR_EMAIL="owner@example.com"
export GIT_COMMITTER_NAME="Fixture Owner" GIT_COMMITTER_EMAIL="owner@example.com"
g() { git -c commit.gpgsign=false -c tag.gpgsign=false "$@"; }

g init -q --bare -b main "$dir/origin.git"
g init -q -b dev "$dir/seed"
cd "$dir/seed"
commit() { echo "$1" > "f$2.txt"; g add "f$2.txt"; g commit -q -m "$1"; }

if [ "$scenario" = s2 ]; then
  printf '#!/usr/bin/env bash\necho "rolling suite: 1 of 12 failed (test_links)"\nexit 1\n' > check.sh
else
  printf '#!/usr/bin/env bash\necho "rolling suite: 12 of 12 passed"\n' > check.sh
fi
chmod +x check.sh
# The fixture has no CI service, so the repository's settings drop the source-ci check and
# check.sh is the whole gate.
mkdir -p .agents
cat > .agents/releasing.json <<'JSON'
{
  "checks": {
    "rolling": {"full-suite": "check.sh is green on {from} at {source} (this repository has no CI service)"},
    "stable": {
      "full-suite": "check.sh is green on {from} at {source} (this repository has no CI service)",
      "release-decision": "the owner's explicit stable-release decision for {tag} is recorded"
    }
  }
}
JSON
g add check.sh .agents/releasing.json
g commit -q -m "chore: add the rolling suite"
g branch rolling
g branch main
g tag -a v0.1.0 -m "First release" main
commit "feat: add the search page (#11)" 1
g switch -q rolling
g merge -q --no-ff -m "Rolling snapshot: 2026-11-15" dev
g tag rolling-2026-11-15
g switch -q main
g merge -q --no-ff -m "Release: v0.1.1" rolling
g tag -a v0.1.1 -m "Search page" main
g switch -q dev
commit "feat: export results as CSV (#12)" 2
commit "fix: keep filters after reload (#13)" 3
commit "docs: explain the CSV columns (#14)" 4
if [ "$scenario" = s2 ]; then
  g switch -q rolling
  g merge -q --no-ff -m "Rolling snapshot: 2026-11-20" dev
  g tag rolling-2026-11-20
  g switch -q dev
fi
g push -q "$dir/origin.git" dev rolling main --tags
cd "$dir"
rm -rf seed
g clone -q -b main origin.git work
echo "fixture ready: $dir/work (origin: $dir/origin.git)"
