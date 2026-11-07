#!/usr/bin/env bash
# Read-only status of every LatteCrew component. Run on the Mac; it reaches the GPU host over ssh.
#   preflight.sh [gpu-host-alias]      default alias: latte
# Prints one line per check: OK / MISSING / DOWN, plus a hint. Changes nothing.
H=${1:-latte}
ok(){ printf '  %-34s %s\n' "$1" "$2"; }
echo "== Mac"
command -v claude >/dev/null && ok claude-code OK || ok claude-code "MISSING (install Claude Code)"
command -v kirocrew >/dev/null && ok kirocrew OK || ok kirocrew "MISSING (install Kiro Crew)"
command -v codex >/dev/null && ok codex-cli OK || ok codex-cli "missing (optional: @codex bot, planner arm)"
[ -x ~/.local/bin/latte-crew-mcp ] && ok latte-crew-mcp OK || ok latte-crew-mcp "MISSING (gateways/mac/install.sh)"
grep -q latte-crew ~/.kiro/crew/mcp.json 2>/dev/null && ok kiro-mcp-entry OK || ok kiro-mcp-entry "MISSING (merge mcp.json.example, kirocrew setup --agent-only)"
lsof -nP -iTCP:18100 -sTCP:LISTEN >/dev/null 2>&1 && ok model-tunnel-18100 OK || ok model-tunnel-18100 "down (optional LaunchAgent)"
echo "== ssh $H"
if ! ssh -o BatchMode=yes -o ConnectTimeout=8 "$H" true 2>/dev/null; then ok ssh "DOWN (fix ~/.ssh/config Host $H, keys, Tailscale)"; exit 1; fi
ok ssh OK
ssh -o BatchMode=yes "$H" 'bash -s' <<'R'
ok(){ printf '  %-34s %s\n' "$1" "$2"; }
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null | sed 's/^/  gpu: /' || ok gpu MISSING
command -v claude >/dev/null || [ -x ~/.local/bin/claude ] && ok claude-code OK || ok claude-code MISSING
command -v opencode >/dev/null || ls ~/.nvm/versions/node/*/bin/opencode >/dev/null 2>&1 && ok opencode OK || ok opencode "MISSING (npm i -g opencode-ai)"
[ -x ~/latte-models/env/bin/vllm ] && ok vllm-env OK || ok vllm-env "MISSING (models/install.sh)"
for s in llama-swap crewd kirocrew-qwen media-bot; do st=$(systemctl --user is-active $s 2>/dev/null); ok "user service $s" "${st:-absent}"; done
st=$(systemctl is-active kirocrew 2>/dev/null); ok "system service kirocrew" "${st:-absent}"
curl -s -m 3 127.0.0.1:8100/v1/models >/dev/null && ok llama-swap-api OK || ok llama-swap-api DOWN
[ -f ~/latte-crew/config.json ] && ok crew-config OK || ok crew-config "MISSING (crew/install.sh)"
[ -f ~/.config/latte-media/env ] && ok media-env present || ok media-env "absent (media bots optional)"
loginctl show-user "$USER" -p Linger 2>/dev/null | grep -q yes && ok linger OK || ok linger "OFF (sudo loginctl enable-linger $USER)"
systemctl is-enabled suspend.target 2>/dev/null | grep -q masked && ok no-suspend OK || ok no-suspend "suspend not masked"
R
