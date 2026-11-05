#!/usr/bin/env bash
# Run the acceptance tests for one drill (or all of them).
#   ./check.sh a1                 # test your mine/a1_*.py
#   ./check.sh a1 -x              # extra args go to pytest
#   ./check.sh all                # every drill
#   ./check.sh a1 --solutions     # run the reference solution instead (DRILL_IMPL=solutions)
set -euo pipefail
cd "$(dirname "$0")"

id="${1:-all}"
shift || true
args=()
for a in "$@"; do
  if [[ "$a" == "--solutions" ]]; then export DRILL_IMPL=solutions; else args+=("$a"); fi
done

if [[ "$id" == "all" ]]; then
  targets=(tests)
else
  shopt -s nullglob
  targets=(tests/test_"${id}"_*.py)
  if (( ${#targets[@]} == 0 )); then
    echo "no test file matches tests/test_${id}_*.py" >&2
    exit 1
  fi
fi

if [[ -x .venv/bin/pytest ]]; then
  py=(.venv/bin/pytest)
elif python3 -c "import pytest" 2>/dev/null; then
  py=(python3 -m pytest)
else
  echo "first run: creating .venv with pytest" >&2
  python3 -m venv .venv && .venv/bin/pip install -q pytest numpy
  py=(.venv/bin/pytest)
fi
exec "${py[@]}" -q "${targets[@]}" ${args[@]+"${args[@]}"}
