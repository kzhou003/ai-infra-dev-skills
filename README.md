# ai-infra-dev-skills

Claude Code skills for learning, contributing to and running AI infrastructure, each in an English and a Chinese version:

| Skill | What it produces |
|---|---|
| [`read-codebase`](skills/read-codebase/SKILL.md) · [`read-codebase-zh`](skills/read-codebase-zh/SKILL.md) | A **code-wiki style report** of an open-source codebase: one self-contained HTML page plus a PDF. It covers the problem, requirements / goals / constraints, architecture, component connections, end-to-end lifecycle, diagrams, analogies, license, contribution paths and source links pinned to a commit. |
| [`practice-drills`](skills/practice-drills/SKILL.md) · [`practice-drills-zh`](skills/practice-drills-zh/SKILL.md) | A **hands-on drills repository** with domain knowledge pages, exercises, tests, commented reference solutions, hints, diagrams and a PDF book. |
| [`rederive`](skills/rederive/SKILL.md) · [`rederive-zh`](skills/rederive-zh/SKILL.md) | **Socratic, first-principles codebase learning.** The agent turns a repository's hardest design decisions into a sequence of problems, reveals constraints one at a time, lets the user derive the design, then compares it with the implementation. The Chinese version adds AI infrastructure tracks for serving, training, GPU kernels, compilers, distributed systems and agent orchestration. |
| [`lattecrew-setup`](skills/lattecrew-setup/SKILL.md) · [`lattecrew-setup-zh`](skills/lattecrew-setup-zh/SKILL.md) | A **working LatteCrew** on the user's machines: a local-first AI team with Claude Code and Codex planning/reviewing, a local Qwen writing code, multimodal models sharing the GPU, and Slack integration via Kiro Crew and the crewd job runner. |

The skills come from building [nano-vllm-omni-drills](https://github.com/kzhou003/nano-vllm-omni-drills), [gpu-kernel-drills](https://kzhou003.github.io/gpu-kernel-drills/), ai-compiler-drills, LatteCrew and several codebase reports.

## Install

```bash
git clone https://github.com/kzhou003/ai-infra-dev-skills.git
cd ai-infra-dev-skills
./install.sh              # symlinks all skills into ~/.claude/skills/
./install.sh --copy       # or copy them
./install.sh --project    # or install into ./.claude/skills of the current project
```

Then ask Claude Code, for example:
- "Analyze https://github.com/vllm-project/vllm and generate an HTML/PDF source guide." → `read-codebase`
- "帮我分析理解一下 DeepSeek Harness 的架构和源码，写成 HTML 和 PDF" → `read-codebase-zh`
- "Make me 12 drills on LLM serving schedulers and KV-cache management." → `practice-drills`
- "做一套 FlashInfer 的练习题，中文" → `practice-drills-zh`
- "Walk me through deriving the design of vLLM's scheduler. Don't tell me the answer upfront." → `rederive`
- "带我从零推导 vLLM 为什么需要 continuous batching，不要直接讲答案。" → `rederive-zh`
- "Set up a local-first AI agent team with Slack integration." → `lattecrew-setup`

Requirements: Python 3.10+ and Google Chrome or Chromium for the report/drills toolkits; Git for source history and pinned links. `gh` / `GITHUB_TOKEN` is optional.

## Layout

```
skills/<name>/SKILL.md        skill workflow, rules and safety boundaries
skills/<name>/reference/      syntax, templates and quality checklists where needed
skills/<name>/toolkit/        self-contained tools for report and drills skills
skills/<name>/scripts/        helper scripts bundled with a skill (e.g. rederive)
toolkit/                      canonical report/drills builders and validators
docs/                         canonical authoring references
examples/                     worked examples
tools/                        sync and self-test utilities
```

## License

MIT for this repository's own content (see [LICENSE](LICENSE)). Third-party skill adaptations retain their upstream attribution and license notices where applicable.
