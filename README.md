# ai-infra-dev-skills

Claude Code skills for learning and contributing to AI-infrastructure codebases, each in an English and a Chinese version:

| Skill | What it produces |
|---|---|
| [`read-codebase`](skills/read-codebase/SKILL.md) · [`read-codebase-zh`](skills/read-codebase-zh/SKILL.md) | A **code-wiki style report** of an open-source codebase: one self-contained HTML page plus a PDF. It covers the problem, the requirements / goals / constraints, the architecture, how the components connect and the end-to-end lifecycle, with React-Flow-style diagrams, step-through animations, analogies, the license, how to contribute, and 60–150 source links pinned to a commit and verified at build time. |
| [`practice-drills`](skills/practice-drills/SKILL.md) · [`practice-drills-zh`](skills/practice-drills-zh/SKILL.md) | A **drills repository** for a domain. It has HTML knowledge pages, one-hour core exercises (`mine/` skeletons + `tests/`), heavily commented `solutions/`, and one explainer + hints page per drill (diagram, analogy, step-through animation, I/O examples, L1/L2/L3 hints, follow-ups linked to the real source), plus a PDF book. Everything runs on CPU with `./check.sh`. |

The skills come out of building [nano-vllm-omni-drills](https://github.com/kzhou003/nano-vllm-omni-drills), [gpu-kernel-drills](https://kzhou003.github.io/gpu-kernel-drills/), ai-compiler-drills and several codebase reports. Each `SKILL.md` writes down the workflow, the page templates and the quality bar that those projects converged on.

## Install

```bash
git clone https://github.com/kzhou003/ai-infra-dev-skills.git
cd ai-infra-dev-skills
./install.sh              # symlinks all four skills into ~/.claude/skills/
./install.sh --copy       # or copy them
./install.sh --project    # or install into ./.claude/skills of the current project
```

Then ask Claude Code, for example:
- "Analyze https://github.com/luminal-ai/luminal: what it does, the hard parts, how they are solved. HTML report with diagrams." → `read-codebase`
- "帮我分析理解一下 RSSHub + Folo 的原理和源码，写成 HTML 和 PDF" → `read-codebase-zh`
- "Make me 12 drills on LLM serving schedulers and KV-cache management, like nano-vllm-omni-drills" → `practice-drills`
- "做一套 FlashInfer 的练习题，中文" → `practice-drills-zh`

Requirements: Python 3.10+ and Google Chrome or Chromium (for PDFs and screenshots). `toolkit/run.sh` creates a private venv with `markdown-it-py` on first use. `git` is needed for pinned links to local clones; `gh` / `GITHUB_TOKEN` is optional (it raises the API rate limit when there is no local clone).

## Layout

```
skills/<name>/SKILL.md        the skill: workflow, rules, don'ts
skills/<name>/reference/      syntax.md (authoring syntax) · outline.md or structure.md (templates) · checklist.md
skills/<name>/toolkit/        copy of toolkit/ (each skill is self-contained once installed)
skills/<name>/examples/       copy of the matching example's sources
toolkit/                      canonical toolkit: renderer, builders, stub generator, PDF, screenshots, link check
docs/syntax.{en,zh}.md        canonical syntax reference
examples/                     full worked examples, built: report.html/.pdf, index.html, hints/, PDF book
tools/sync.py                 copies toolkit/, docs/ and examples/ into skills/ (--check in CI)
tools/selftest.sh             builds both examples strictly and checks the drills both ways (--full: + PDF, shots, links)
```

## The toolkit

| Script | Does |
|---|---|
| `build_report.py report.json [--strict --shots --links --pdf]` | Markdown → one code-wiki HTML page (left TOC, diagrams, steppers, pinned links) → PDF |
| `build_drills.py drills.json [--strict --shots --links --pdf]` | hub page + knowledge pages + one hint page per drill → PDF book |
| `gen_stubs.py drills.json [--check]` | `solutions/` → `mine/` skeletons: signatures + docstrings kept, bodies → `NotImplementedError`, `given` names copied |
| `shots.py page.html out/` | PNG screenshots of every diagram, so they get looked at, not just linted |
| `make_pdf.py page.html out.pdf` | headless-Chrome PDF in print mode (light theme, every hint and step expanded) |
| `check_links.py pages...` | every external link must answer 200 |

What `--strict` enforces: every `[[repo:path#L…]]` / `[[repo:path@Symbol]]` link resolves at the pinned SHA (file exists, line within the file, symbol found); embedded files exist; diagrams have no overlapping nodes, no text wider than its box, and no edge label that cannot fit between its nodes; and the per-page minimums for diagrams, step-throughs, analogies and hint levels are met.

Examples: [`examples/read-codebase-zh-rsshub-folo`](examples/read-codebase-zh-rsshub-folo/) (open `report.html` or `report.pdf`) and [`examples/practice-drills-en-paged-kv`](examples/practice-drills-en-paged-kv/) (open `index.html`; `./check.sh all --solutions`).

---

## 中文说明

四个 Claude Code skill，用来学习 AI infra 代码库并为它们贡献代码，每个都有中英文两版：

- **`read-codebase-zh` / `read-codebase`**：把一个开源代码库写成 **code-wiki 风格的报告**，输出单个 HTML 和 PDF。内容包括：要解决的问题；要求、目标和限制；架构，以及各组件怎么连接；端到端的生命周期；React Flow 风格的图和逐步演示动画；类比；开源许可证；怎么贡献。还有 60–150 个固定到 commit、构建时逐条校验的源码链接。
- **`practice-drills-zh` / `practice-drills`**：为一个领域做一套**练习仓库**。包括：领域知识 HTML 页；一小时一道的核心题（`mine/` 骨架 + `tests/` 验收测试）；带详细注释的 `solutions/`；每道题一页讲解与提示（图解、类比、逐步演示动画、I/O 示例、L1/L2/L3 三级提示、追问与对照源码）；以及 PDF 手册。全部在 CPU 上用 `./check.sh` 验收。

安装：`./install.sh`（把四个 skill 软链接到 `~/.claude/skills/`），然后直接对 Claude Code 说“帮我分析理解一下 xxx，写成 HTML 报告”或“做一套 xxx 的练习题”。

这些 skill 总结自 nano-vllm-omni-drills、gpu-kernel-drills、ai-compiler-drills 和几份源码导读的制作过程。每个 `SKILL.md` 都写明了流程、页面模板和质量标准：例如每张图都要截图看过才能交付，演示里的数字必须运行参考解得出，历史类说法必须用 GitHub API 核实。

## License

MIT for this repository's own content (see [LICENSE](LICENSE)). The examples link to upstream projects at pinned commits; that code keeps its own licenses.
