---
name: practice-drills-zh
description: 用中文为一个技术领域（AI infra、LLM 推理服务、GPU kernel、编译器、分布式系统或某个代码库）做一套动手练习仓库。仓库里有：讲解领域知识的 HTML 页面；核心练习题（接口骨架 + 验收测试）；带详细注释的参考解；每道题一页讲解与提示，配 React Flow 风格的图、类比、逐步演示动画、I/O 示例和三级剧透提示；以及一本 PDF 手册。全部在 CPU 上用 ./check.sh 验收。当用户要求做练习题、drills、刷题、面试准备、自学课程或训练营，或者说“像 nano-vllm-omni-drills / gpu-kernel-drills 那样”时使用。英文版用 practice-drills。
---

# 练习题：领域知识页 + 核心题 + 测试 + 带注释的参考解 + 讲解提示页

交付物是一个 git 仓库，学习者 clone 下来就能按“一次一小时”的节奏练：

```
<name>-drills/
  README.md                  简介、快速开始、进度表（每题一个 ☐）；开头一段英文简介，正文中文
  drills.json                唯一的配置来源：标题、语言、pins、track、题目、知识页
  check.sh  drill.py  pytest.ini  .gitignore
  mine/<stem>.py             接口骨架，所有函数都 raise NotImplementedError   ← 学习者在这里写
  tests/test_<stem>.py       验收测试（CPU、确定性、每个 < 1 秒）
  solutions/<stem>.py        参考解，注释讲清“为什么”
  src/index.md               首页说明：怎么用、环境、建议顺序
  src/knowledge/<name>.md    领域知识页
  src/hints/<stem>.md        每题一页：讲解 + 三级提示
  index.html  knowledge/*.html  hints/*.html  <name>.pdf      ← 构建产物，一起提交
```

本 skill 自带：

| 路径 | 作用 |
|---|---|
| `toolkit/run.sh` | 用带 `markdown-it-py` 的 Python 运行工具脚本 |
| `toolkit/build_drills.py` | 生成首页 + 知识页 + 提示页（可加 `--pdf --shots --links --strict`） |
| `toolkit/gen_stubs.py` | `solutions/` → `mine/` 骨架（保留签名、docstring 和 `given` 里的辅助代码） |
| `toolkit/templates/drills/` | 新仓库要复制的 `check.sh`、`drill.py`、`pytest.ini`、`gitignore` |
| `reference/syntax.md` | **写页面前先读**：容器、流程图 DSL、逐步演示、格子、代码嵌入、固定链接 |
| `reference/structure.md` | drills.json 结构、提示页和知识页模板、README 模板 |
| `reference/checklist.md` | 质量标准；回复用户前逐条过一遍 |
| `examples/paged-kv/` | 完整的小范例：2 道题，对照 vLLM v1 的 block pool 和 scheduler |

## 流程

### 1. 确定范围（能推断的用合理默认值，推断不了的才问）
- **领域和对照项目**：题目要对照真实代码。选 1–3 个参考仓库（如 vLLM、SGLang、FlashInfer、Triton）和最关键的子系统。
- **规模**：第一版 8–16 题，每题 30–75 分钟（用户可以再要更多），分成 2–5 个 track，从基础到整合排列。题目之间有依赖要写明。
- **语言**：正文用中文（本 skill）。代码、标识符、测试名一律英文。难度用“易 / 中 / 难”。
- 位置：默认 `~/development/<name>-drills/`。用户给了 GitHub 地址的话，那就是 remote。

用一条消息贴出题目表（编号、题目、分钟、对照的真实函数），然后继续。除非用户要求先审，否则不要停下来等确认。

### 2. 研究并固定版本
clone 对照仓库，把 SHA 写进 `drills.json → pins`（带 `local` 路径），读每个机制的真实实现。记下每题对照的函数和行，它们会成为“面试官追问 & 对照源码”里的链接。说法（默认值、执行顺序、边界行为）都要在代码里核实。

### 3. 设计每道题（一个机制，一小时）
- **一个核心机制**，从业者必须真正理解的那种（一次调度、一个 block 分配器、一个 attention mask、一个 layout 函数、一个重试协议……）。不是玩具，也不是整个系统。
- **纯 Python**（+ numpy；确实需要时用 CPU 版 torch），确定性，不联网、不用 GPU。硬件或分布式效应用简单的模拟表示（假时钟、模拟 worker、按字节计数）。
- **接口规范写在参考解的模块 docstring 和函数 docstring 里**，因为它们会被原样复制进骨架。测试检查的每一条行为都必须写在那里，不能有隐藏要求。
- **`given`**（在 drills.json 里）：学习者不该花时间写的辅助函数、数据类、常量，让这一小时都花在机制本身上。
- 题目名写清楚做的是什么；分钟数和难度要实事求是。

### 4. 每道题按这个顺序做
1. **先写参考解**（`solutions/<stem>.py`）。注释讲“为什么”：维护的是什么不变量、为什么是这个顺序、按直觉写会坏在哪里、复杂度、真实项目哪里不同。函数体内的注释在骨架里会被删掉，所以解释可以放心写在函数体里。
2. **写测试**（`tests/test_<stem>.py`）：用 `from drill import load; m = load("<stem>")` 加载。测行为、边界情况和不变量：提示页上列出的每个易错点，都要有一个能抓住它的测试。测试名要有描述性（`test_failed_allocation_changes_nothing`）。用较长的随机或模拟运行检查不变量（预算从不超、没有泄漏）。
3. `bash <skill>/toolkit/run.sh gen_stubs.py drills.json` → 生成 `mine/<stem>.py`。
4. **两个方向都要验证**：`DRILL_IMPL=solutions ./check.sh <id>` 必须通过；`./check.sh <id>` 必须因 NotImplementedError 失败。如果某个测试在骨架上也能通过，它什么都没测。
5. **写提示页**（`src/hints/<stem>.md`），按 `reference/structure.md` 的结构：题面速览 → 直觉与类比 → 图解 → 逐步演示 → 易错点 → L1 / L2 / L3 三级提示 → 参考解（嵌入）→ 面试官追问 & 对照源码。**示例和演示里的每个数字都要写个小脚本运行参考解得出**，不要手算。

### 5. 知识页（`src/knowledge/*.md`）
1–4 页，让题目变得有意义：这个领域在解决什么问题、朴素做法为什么不行、关键机制（配图，并链到真实代码）、一两个类比，最后一张表“题目 → 它复刻了什么 → 源码”。在题目写完之后再写，这样讲的正好是题目需要的东西。

### 6. README、构建、看图、修改
- 按 `reference/structure.md` 里的模板写 README：开头一段英文简介，然后中文的简介、快速开始、目录结构、怎么做一道题、带 ☐ 的进度表、首页和 PDF 的链接。
- `bash <skill>/toolkit/run.sh build_drills.py drills.json --strict --shots`。修掉所有错误，然后**逐张打开 `.shots/` 下的 PNG 去看**：没有连线穿过节点、没有标签压在节点上、没有可以避免的交叉。改到干净为止。
- `--links`（外链返回 200），再 `--pdf`，抽查几页。
- 最后一轮：`DRILL_IMPL=solutions ./check.sh all` 全过；`./check.sh all` 每题都失败；`gen_stubs.py --check` 通过。

### 7. Git 与发布（用户要求时才做）
用户要求了才 commit 和 push。要求了的话：`git init -b main`，写清楚的 commit message，加 remote，push。可选：开启 GitHub Pages（`main` 分支根目录），让 `index.html` 可以在线浏览（`gh api -X POST repos/O/R/pages -f 'source[branch]=main' -f 'source[path]=/'`），并验证线上地址。

### 8. 回复用户
给出路径、题目表、两个方向的测试结果、看图检查的结果、PDF 页数，以及 push 之后的仓库地址或 Pages 地址。

## 不要做的事
- 不要测实现细节（私有名字、具体数据结构），测可观察的行为。
- docstring 和测试不能矛盾；docstring 就是规范。
- 演示里的数字不要手算，运行参考解。
- 不要把答案留在骨架里：函数体会被替换，所以解释写在函数体注释里。
- 不要出需要 GPU、联网或大文件下载的题。
- 没看过截图的图不要交付。
