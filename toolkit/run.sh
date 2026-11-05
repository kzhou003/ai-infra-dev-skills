#!/usr/bin/env bash
# Run a toolkit script with a Python that has markdown-it-py.
#   bash run.sh build_report.py path/to/report.json --strict --shots --pdf
#   bash run.sh build_drills.py path/to/drills.json --strict --shots --pdf
# Uses $PYTHON if set, else python3 if it already has markdown_it, else a private venv in
# ~/.cache/ai-infra-dev-skills/venv (created on first use).
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
script="${1:?usage: run.sh <script.py> [args...]}"; shift
py="${PYTHON:-}"
if [[ -z "$py" ]]; then
  if python3 -c "import markdown_it" 2>/dev/null; then
    py=python3
  else
    venv="${XDG_CACHE_HOME:-$HOME/.cache}/ai-infra-dev-skills/venv"
    if [[ ! -x "$venv/bin/python" ]]; then
      python3 -m venv "$venv"
      "$venv/bin/pip" install -q markdown-it-py pytest
    fi
    py="$venv/bin/python"
  fi
fi
exec "$py" "$here/$script" "$@"
