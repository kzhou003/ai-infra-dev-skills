#!/usr/bin/env bash
# Install the skills into Claude Code.
#   ./install.sh            symlink every skill into ~/.claude/skills/ (updates with git pull)
#   ./install.sh --copy     copy instead of symlink
#   ./install.sh --project  install into ./.claude/skills/ of the current directory instead
#   ./install.sh read-codebase practice-drills-zh   only these skills
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mode=link; dest="$HOME/.claude/skills"; names=()
for a in "$@"; do
  case "$a" in
    --copy) mode=copy ;;
    --project) dest="$PWD/.claude/skills" ;;
    -h|--help) sed -n 2,6p "$0"; exit 0 ;;
    *) names+=("$a") ;;
  esac
done
if (( ${#names[@]} == 0 )); then
  for d in "$repo"/skills/*/; do names+=("$(basename "$d")"); done
fi
mkdir -p "$dest"
for n in "${names[@]}"; do
  src="$repo/skills/$n"
  [[ -f "$src/SKILL.md" ]] || { echo "no such skill: $n" >&2; exit 1; }
  target="$dest/$n"
  if [[ -L "$target" || -e "$target" ]]; then rm -rf "$target"; fi
  if [[ "$mode" == copy ]]; then cp -R "$src" "$target"; else ln -s "$src" "$target"; fi
  echo "installed $n -> $target ($mode)"
done
echo "Restart Claude Code (or start a new session) to pick up new skills."
