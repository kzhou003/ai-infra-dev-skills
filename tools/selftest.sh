#!/usr/bin/env bash
# End-to-end self-test: toolkit copies in sync, both examples build cleanly (strict), the drills
# example passes with solutions and fails with stubs. Add --full for screenshots, links and PDFs.
set -euo pipefail
cd "$(dirname "$0")/.."
run=(bash toolkit/run.sh)
extra=()
[[ "${1:-}" == "--full" ]] && extra=(--shots --links --pdf)

echo "== skills are in sync with toolkit/, docs/ and examples/"
python3 tools/sync.py --check

echo "== read-codebase example (RSSHub + Folo, zh)"
"${run[@]}" build_report.py examples/read-codebase-zh-rsshub-folo/report.json --strict ${extra[@]+"${extra[@]}"}

echo "== practice-drills example (paged KV, en)"
ex=examples/practice-drills-en-paged-kv
"${run[@]}" build_drills.py $ex/drills.json --strict ${extra[@]+"${extra[@]}"}
"${run[@]}" gen_stubs.py $ex/drills.json --check
py="${PYTHON:-${XDG_CACHE_HOME:-$HOME/.cache}/ai-infra-dev-skills/venv/bin/python}"
command -v "$py" >/dev/null 2>&1 || py=python3
(cd $ex && DRILL_IMPL=solutions "$py" -m pytest -q -p no:cacheprovider | tail -1)
if (cd $ex && "$py" -m pytest -q -p no:cacheprovider >/dev/null 2>&1); then
  echo "FAIL: some test passes on the stubs"; exit 1
else
  echo "stubs fail as expected"
fi
echo "== all good"
