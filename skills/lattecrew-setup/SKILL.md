---
name: lattecrew-setup
description: Set up, extend, check or repair a LatteCrew system from the kzhou003/lattecrew repo — a local-first AI team where Claude Code and Codex plan and review, a local Qwen model on a GPU machine writes code, and image, speech and video models share the same GPU, all reachable from Slack through Kiro Crew gateways and run by the crewd job runner. Use when the user wants to build an AI team on their own GPU box, connect Kiro Crew to Claude Code on another machine, add Slack bots for local models, serve models behind llama-swap, install crewd, add a bot or model to an existing LatteCrew, or asks why some part of it is down. Writes English; use lattecrew-setup-zh for Chinese.
---

# Set up LatteCrew

LatteCrew is a working system, not a template: every script in [kzhou003/lattecrew](https://github.com/kzhou003/lattecrew) ran on a real Mac + RTX 5090 pair. Your job is to reproduce it on the user's machines, adapted to what they have, phase by phase, with a check after each phase. Do the work yourself; stop only for steps that need the user's hands (sudo passwords, Slack app creation, tokens, logins).

## Read first

1. Clone or update the repo on the machine you run on: `git clone https://github.com/kzhou003/lattecrew.git` (or `git -C lattecrew pull`).
2. Read `README.md`, `docs/setup.md` (the runbook you will follow), `docs/architecture.md`, `docs/security.md` and `docs/troubleshooting.md`. The per-directory READMEs say what each file does. Follow the repo when it disagrees with this skill: the repo is the source of truth.
3. Run `reference/preflight.sh <gpu-host-alias>` from this skill. It is read-only and prints the state of every component, so you can skip what already works. Run it again at the end.

## Gather facts before changing anything

Detect these yourself (commands, files), and ask the user only for what you cannot detect:

| Fact | How to find it |
|---|---|
| GPU host and SSH alias | `~/.ssh/config`, `ssh -o BatchMode=yes <alias> true` |
| GPU model and memory | `nvidia-smi --query-gpu=name,memory.total --format=csv` |
| OS, Python 3.12, Node 22, CUDA driver | `python3.12 --version`, `node -v`, `nvidia-smi` |
| Claude Code logged in on both machines | `claude auth status` |
| Kiro Crew installed, which gateways exist | `kirocrew doctor`, `~/.kiro/crew*/` |
| Which bots the user wants | ask: coding bots (`@claude`, `@codex`, `@qwen`) and media bots (`@z-image`, `@qwen-tts`, `@wan`) |
| Slack workspace | ask; the user creates the apps |

Adapt to the hardware. The repo targets 32 GB. With 24 GB, keep Qwen3.8-27B AWQ but lower `CTX` (32768) and `SEQS` (1) in `serve-qwen.sh`, and drop Wan or keep its CPU offload. Below 24 GB, pick a smaller coder (a 14B AWQ model) through `MODEL=`, and say what that costs in quality. Without an NVIDIA GPU, set up only crewd with Claude jobs (`crew task`, `crew team`) and skip the model layer.

## Phases

Follow `docs/setup.md` in this order. Each phase ends with its **Check**; do not continue until it passes. Report each phase in one or two lines as you finish it.

| Phase | Do | Needs the user for |
|---|---|---|
| 0 Access | SSH alias with `ControlMaster`; mask suspend; `loginctl enable-linger`; Claude Code and OpenCode on the GPU host | sudo password; Tailscale login |
| 1 Models | `models/install.sh` on the GPU host (download llama-swap first) | – (weights are large: check disk with `df -h ~` first) |
| 2 crewd | `crew/install.sh`; set `repo_roots` and budgets in `~/latte-crew/config.json` | budget numbers |
| 3 Gateways | Mac: `gateways/mac/install.sh`, merge `mcp.json`, Bot `CLAUDE.md` + `claude mcp add -s local`; GPU host: `kirocrew service install`, `gateways/latte/setup-qwen-gateway.sh` | sudo; Kiro dashboard steps |
| 4 Slack | apps from `slack/manifest-*.yaml`; `kirocrew setup --slack` per gateway; `trusted_bot_ids`, `trusted_bot_turn_limit: 1`; `media-bot/install.sh` | creating and installing apps; pasting tokens into files |
| 5 Phone | Tailscale Serve for the dashboard (optional) | enabling Serve once |
| 6 Verify | end-to-end checks below; `reference/preflight.sh` all green | – |

## End-to-end verification

Run all of these and show the user the results:

1. `crew task "Say hello in one sentence." --risk low` on the GPU host → `done` within two minutes.
2. `crew local "Add a docstring to one function" --repo <a test repo> --risk low` → Qwen commits, Claude reviews, state `ready`.
3. From the Mac, through Claude Code or the Kiro dashboard: ask the Bot to list repos on the GPU host → it calls `crew_repos`.
4. In Slack: DM each bot; mention two bots in the team channel; ask `@z-image` for an image if installed.
5. `python3 -m unittest discover -s tests` in the repo on the GPU host (Linux) → `OK`.

## Rules

- **Tokens never go through chat.** Slack tokens go into `~/.config/latte-media/env` (mode 600) or Kiro's own `setup --slack` prompt, typed by the user. Never print them, never commit them, never pass them on a command line.
- **Do not weaken guards.** Keep the Landlock sandbox, the push wall, `disallowed_tools`, the OpenCode permissions and the AppArmor profile. Do not set `agent.sandbox off`. If something fails because of a guard, fix the cause.
- **Ask before persistence on the Mac.** LaunchAgents, login items and cron jobs on the user's laptop need their approval; give them the command instead of running it if they have not said yes. User services on the GPU host are part of the setup the user asked for.
- **Agents never push or merge.** crewd keeps results on `crew/<id>` branches. Do not change that.
- **Never answer a `need_human` question or approve a SPEC for the user.**
- **Use the repo's scripts** rather than retyping their contents. If a script needs a change for this machine, make it in a copy or with an env var, and tell the user what differs from upstream.
- Over SSH, never `pkill -f <pattern>` when the remote command line contains the pattern; it kills your own session. Use `models/bin/stop-gpu.sh` or `systemctl --user stop`.

## Known traps (from `docs/troubleshooting.md`)

- `opencode run` waits on stdin forever unless stdin is closed; crewd also sets `PWD` and `--dir` to the worktree.
- Keep OpenCode's **global** output limit at 8,192: Kiro's `@qwen` prompt is ~47K tokens and a larger output reserve sends it into a compaction loop. crewd raises the limit to 32,768 per process through `crew/opencode-permissions.json`.
- A desktop browser can hold ~2 GB of VRAM; `serve-qwen.sh` sizes memory from what is free.
- Kiro Bots chat through a conductor that mounts no user MCP: delegation needs the Bot workspace's `CLAUDE.md` and `claude mcp add -s local`.
- `slack.channels` can only be set by editing Kiro's `config.json`.
- Two bots in one channel reply to each other's footers unless `slack.trusted_bot_turn_limit` is 1.

## Extending

- **Another model**: add a `serve-*.sh` (bind 127.0.0.1, log to `~/latte-models/logs/`), an entry in `llama-swap.yaml` with a free port and `ttl`, and, for a media model, a kind in `media-bot/media_bot.py` plus a Slack manifest. Hold `gpu.lock` around GPU work.
- **Faster local coder**: MTP speculative decoding (`EXTRA` in the llama-swap entry, see `docs/setup.md`) measured 1.5–2× decode speed for ~40% of the KV cache.
- **Measure after changes**: `bench/README.md` lists probes for every layer.

## Done means

`reference/preflight.sh` shows every component the user chose as OK or active, the five end-to-end checks pass, and you have told the user: which bots exist and what each does, where logs live (`~/latte-models/logs`, `crew logs <job>`, `journalctl --user -u <service>`), and anything left for them to do.
