---
name: lattecrew-setup-zh
description: 用中文，按 kzhou003/LatteCrew 仓库搭建、扩展、检查或修复一套 LatteCrew：以本地为主的 AI 团队。Claude Code 和 Codex 负责规划和审查，GPU 机器上的本地 Qwen 写代码，图像、语音、视频模型共用同一块 GPU；所有成员通过 Kiro Crew 网关接入 Slack，长任务由 crewd 作业系统运行。当用户想在自己的 GPU 机器上搭一个 AI 团队、把 Kiro Crew 接到另一台机器上的 Claude Code、给本地模型加 Slack bot、用 llama-swap 管理模型、安装 crewd、给现有 LatteCrew 加 bot 或模型，或者问某个部分为什么挂了时使用。英文版用 lattecrew-setup。
---

# 搭建 LatteCrew

LatteCrew 是一套真实在用的系统，不是模板：[kzhou003/LatteCrew](https://github.com/kzhou003/LatteCrew) 里的每个脚本都在一台 Mac 加一台 RTX 5090 上跑过。你的任务是按阶段把它在用户的机器上复现出来，根据用户的硬件做调整，每个阶段结束都要检查。能自己做的都自己做；只有需要用户亲自操作的步骤（sudo 密码、创建 Slack app、填 token、登录账号）才停下来请用户处理。

## 先读

1. 在当前机器上克隆或更新仓库：`git clone https://github.com/kzhou003/LatteCrew.git`（已有就 `git -C LatteCrew pull`）。
2. 读 `README.md`、`docs/setup.md`（你要照着执行的操作手册）、`docs/architecture.md`、`docs/security.md`、`docs/troubleshooting.md`。各目录的 README 说明了每个文件的用途。仓库和本 skill 不一致时，以仓库为准。
3. 运行本 skill 的 `reference/preflight.sh <GPU 主机别名>`。它只读不改，会列出每个组件的状态，已经正常的部分可以跳过。全部完成后再跑一次。

## 动手前先摸清情况

下面这些能自己查就自己查，查不到的才问用户：

| 信息 | 怎么查 |
|---|---|
| GPU 主机和 SSH 别名 | `~/.ssh/config`，`ssh -o BatchMode=yes <别名> true` |
| GPU 型号和显存 | `nvidia-smi --query-gpu=name,memory.total --format=csv` |
| 系统、Python 3.12、Node 22、CUDA 驱动 | `python3.12 --version`、`node -v`、`nvidia-smi` |
| 两台机器上 Claude Code 是否已登录 | `claude auth status` |
| Kiro Crew 是否安装、已有哪些网关 | `kirocrew doctor`、`~/.kiro/crew*/` |
| 用户想要哪些 bot | 问用户：编程类（`@claude`、`@codex`、`@qwen`），媒体类（`@z-image`、`@qwen-tts`、`@wan`） |
| Slack 工作区 | 问用户；Slack app 由用户自己创建 |

按硬件调整。仓库默认 32 GB 显存。24 GB 时，仍可用 Qwen3.8-27B AWQ，但在 `serve-qwen.sh` 里调低 `CTX`（32768）和 `SEQS`（1），Wan 去掉或保持 CPU offload。低于 24 GB 时，用 `MODEL=` 换一个更小的编程模型（例如 14B AWQ），并说明质量上的代价。没有 NVIDIA GPU 时，只装 crewd 跑 Claude 作业（`crew task`、`crew team`），跳过模型层。

## 阶段

按 `docs/setup.md` 的顺序执行。每个阶段末尾都有 **Check**，通过了才能进入下一阶段。每完成一个阶段，用一两句话告诉用户。

| 阶段 | 做什么 | 需要用户做的 |
|---|---|---|
| 0 访问 | SSH 别名加 `ControlMaster`；禁止休眠；`loginctl enable-linger`；GPU 主机上装 Claude Code 和 OpenCode | sudo 密码；Tailscale 登录 |
| 1 模型 | 在 GPU 主机上运行 `models/install.sh`（先下载 llama-swap） | 无（权重很大，先用 `df -h ~` 看磁盘） |
| 2 crewd | `crew/install.sh`；在 `~/latte-crew/config.json` 里设置 `repo_roots` 和预算 | 预算数额 |
| 3 网关 | Mac：`gateways/mac/install.sh`、合并 `mcp.json`、Bot 的 `CLAUDE.md` 加 `claude mcp add -s local`；GPU 主机：`kirocrew service install`、`gateways/latte/setup-qwen-gateway.sh` | sudo；Kiro 控制台里的操作 |
| 4 Slack | 用 `slack/manifest-*.yaml` 创建 app；每个网关跑 `kirocrew setup --slack`；设置 `trusted_bot_ids` 和 `trusted_bot_turn_limit: 1`；`media-bot/install.sh` | 创建并安装 app；把 token 填进文件 |
| 5 手机 | 用 Tailscale Serve 开放控制台（可选） | 开启一次 Serve |
| 6 验证 | 下面的端到端检查；`reference/preflight.sh` 全部正常 | 无 |

## 端到端验证

全部运行一遍，把结果给用户看：

1. 在 GPU 主机上 `crew task "Say hello in one sentence." --risk low`，两分钟内变成 `done`。
2. `crew local "Add a docstring to one function" --repo <测试仓库> --risk low`：Qwen 提交，Claude 审查，状态变成 `ready`。
3. 在 Mac 上通过 Claude Code 或 Kiro 控制台，让 Bot 列出 GPU 主机上的仓库，它应该调用 `crew_repos`。
4. Slack 里：给每个 bot 发私信；在团队频道里同时 @ 两个 bot；如果装了 `@z-image`，让它生成一张图。
5. 在 GPU 主机（Linux）上的仓库里跑 `python3 -m unittest discover -s tests`，结果是 `OK`。

## 规则

- **token 不经过聊天。** Slack token 只写进 `~/.config/latte-media/env`（权限 600），或者由用户在 Kiro 的 `setup --slack` 提示里自己输入。不要打印、不要提交、不要放在命令行参数里。
- **不削弱防护。** 保留 Landlock 沙箱、push wall、`disallowed_tools`、OpenCode 权限和 AppArmor 配置。不要设置 `agent.sandbox off`。被防护拦住时，修根因。
- **在 Mac 上加常驻项之前先问。** LaunchAgent、登录项、cron 需要用户同意；没同意就只给出命令，不要执行。GPU 主机上的用户服务属于用户要求的搭建内容。
- **agent 永远不 push、不 merge。** crewd 把结果留在 `crew/<id>` 分支上，不要改这一点。
- **不要替用户回答 `need_human` 问题，也不要替用户批准 SPEC。**
- **直接用仓库里的脚本**，不要重新手打一遍。如果某个脚本要为这台机器修改，改副本或用环境变量，并告诉用户和上游有什么不同。
- 通过 SSH 时，如果远端命令行里本身含有某个字符串，就不要用 `pkill -f <这个字符串>`，否则会杀掉自己的会话。改用 `models/bin/stop-gpu.sh` 或 `systemctl --user stop`。

## 已知的坑（详见 `docs/troubleshooting.md`）

- `opencode run` 不关闭标准输入就会一直等；crewd 还会把 `PWD` 和 `--dir` 设成 worktree。
- OpenCode 的**全局**输出上限保持 8,192：Kiro `@qwen` 的提示约 4.7 万 token，输出预留更大时会陷入压缩循环。crewd 通过 `crew/opencode-permissions.json` 只给自己的进程调到 32,768。
- 桌面浏览器可能占用约 2 GB 显存；`serve-qwen.sh` 会按实际空闲显存来设置。
- Kiro 的 Bot 通过一个不挂载用户 MCP 的 conductor 聊天：要让它委派任务，需要 Bot 工作区里的 `CLAUDE.md` 加上 `claude mcp add -s local`。
- `slack.channels` 只能直接编辑 Kiro 的 `config.json` 来设置。
- 同一个频道里的两个 bot 会互相回复对方的页脚，除非把 `slack.trusted_bot_turn_limit` 设成 1。

## 扩展

- **加一个模型**：写一个 `serve-*.sh`（绑定 127.0.0.1，日志写到 `~/latte-models/logs/`），在 `llama-swap.yaml` 里加一项，用空闲端口并设置 `ttl`；如果是媒体模型，在 `media-bot/media_bot.py` 里加一个类型，再加一个 Slack manifest。用 GPU 时要持有 `gpu.lock`。
- **让本地编程模型更快**：MTP 推测解码（在 llama-swap 条目里设置 `EXTRA`，见 `docs/setup.md`），实测解码快 1.5–2 倍，代价是约 40% 的 KV 缓存。
- **改动后要测量**：`bench/README.md` 列出了每一层的探针。

## 完成的标准

`reference/preflight.sh` 显示用户选择的每个组件都是 OK 或 active，五项端到端检查都通过，并且已经告诉用户：有哪些 bot、各自做什么，日志在哪里（`~/latte-models/logs`、`crew logs <job>`、`journalctl --user -u <服务名>`），以及还有哪些需要用户自己完成。
