# 结构与页面模板：practice-drills-zh

## drills.json

```json
{
  "title": "LLM 推理服务练习",
  "brand": "推理服务练习",                           // 左侧导航里的短名（可选）
  "kicker": "自学练习",                              // 首页标题上方的小字（可选）
  "lede": "一段话：做完之后能写出、讲清楚什么。",
  "lang": "zh",
  "slug": "serving-drills",                          // 进度勾选存在 localStorage 里用的 key
  "repo_url": "https://github.com/me/serving-drills", // 可选：文件链接指向 GitHub
  "pins": {
    "vllm": {"repo": "vllm-project/vllm", "sha": "<40 位>", "local": "~/development/vllm"}
  },
  "tracks": [{"id": "A", "title": "Track A · 显存管理", "desc": "一句话说明这个 track 讲什么。"}],
  "drills": [
    {"id": "A1", "stem": "a1_block_pool", "title": "BlockPool：引用计数、LRU 空闲队列、前缀缓存",
     "minutes": 50, "difficulty": "中", "track": "A",
     "given": ["NoFreeBlocks", "hash_blocks", "BlockPool.ref_count"]}
  ],
  "knowledge": ["overview"],
  "pdf": "serving-drills.pdf",
  "quality": {"flows": 1, "steps": 1, "analogies": 1, "hints": 3}
}
```

- `stem` 是 `mine/`、`tests/test_<stem>.py`、`solutions/`、`src/hints/` 共用的文件名，以小写编号开头（`a1_...`），这样 `./check.sh a1` 能找到它。
- `given` 是原样复制进骨架的名字（`Class`、`Class.method`、`function`、`CONSTANT`）。
- `quality` 是每个提示页的最低要求；加 `--strict` 时不达标就报错。

## 参考解文件模板

```python
"""A1 · <题目> — reference solution.

<两到五行：它在真实系统里是什么，对照哪个函数。可以写中文。>

- <测试检查的规则 1>
- <规则 2 ...>

API
    name(args) -> result        <每个一行；给定的标注 given>
"""
from __future__ import annotations


def given_helper(...):
    """docstring 会保留在骨架里。"""
    ...


class Thing:
    def method(self, x: int) -> int:
        """返回什么、什么时候抛异常。会保留在骨架里。"""
        # “为什么”写在这里：不变量、为什么是这个顺序、直觉写法会坏在哪、
        # 真实项目怎么做（以及为什么不同）。这些注释在骨架里会被删掉。
        ...
```

（模块 docstring 第一行保留 `reference solution` 字样：gen_stubs 会把它替换成 `your implementation (run ./check.sh a1)`。）

## 测试文件模板

```python
import pytest

from drill import load

m = load("a1_block_pool")


def test_<可观察的行为>():
    ...


def test_<提示页上的易错点>_is_handled():
    ...


def test_<不变量>_over_a_long_random_run():
    ...
```

## 提示页模板（`src/hints/<stem>.md`）

```markdown
lede: 一句话：这道题做的是什么、为什么重要。
# A1 · <题目>

## 题面速览
- **在系统中的位置**：<真实系统什么时候调用它>（[[alias:path@Symbol|Symbol]]）。
- **你要实现**：<函数>。<given 的内容> 已经给出。
- **难点在这几条规则**：编号列出 3–5 条。

**验收要点**：<每个测试一句，用 · 连接>

## 直觉与类比
::: callout analogy <具体的、生活里的类比>
<把每个部件的对应关系写明白。>
:::

## 图解：<数据结构 / 算法>
::: flow <标题>
...
cap: <不变量，或者看图时要注意的点>
:::

## 逐步演示
::: steps <带具体规模的场景名>
::: flow
...（一张小图，下面每一步高亮其中的节点）
:::
--- step 初始状态 {hl=...}
<状态，适合的地方用 {{cells: ...}}>
--- step <操作> {hl=...}
<发生了什么、为什么；数字由运行参考解得出>
:::

## 易错点
- **<错误>。** <会出什么问题，哪个测试会抓到>

## 三级提示
::: hint 1 I/O 示例与关键问题
<python 代码块：具体调用和结果（要真的运行过！）>
#### 关键问题
1. ...
:::

::: hint 2 思路与常见坑
<需要维护的状态；4–8 步的算法；坑>
:::

::: hint 3 详解：答案
::: answer 关键问题答案
1. ...
:::
:::

## 参考解
::: solution solutions/<stem>.py
{{code: solutions/<stem>.py}}
:::

## 面试官追问 & 对照源码
- <在这道题基础上延伸的追问>
- <真实系统怎么处理题目里简化掉的部分，带链接>
```

## 知识页模板（`src/knowledge/<name>.md`）

```markdown
lede: 一句话说明这一页讲什么。
# <主题>

## 问题在哪
<没有它会出什么问题；一张“事实 → 后果”的表>

### 解决办法：<机制>
<正文 + ::: flow + 一个类比>

## <机制 2>
...

## 和练习题的对应关系
| 题目 | 复刻了什么 | 源码 |
|---|---|---|
| A1 ... | ... | [[alias:path@Symbol|文件]] |
```

## 首页说明（`src/index.md`）

环境命令（`python3 -m venv .venv && .venv/bin/pip install pytest numpy`）、`./check.sh` 用法、怎么做一道题（读题 5 分钟 → 实现 → 跑测试 → 对照参考解）、建议顺序和依赖。不需要 `lede:` 行。

## README 模板

```markdown
# <name>-drills

<English intro paragraph: N one-hour drills that each rebuild one core mechanism of <domain>,
mirroring <projects> at pinned commits. CPU only. Quick start: `./check.sh a1`. The rest of this
README is in Chinese.>

---

<中文简介：N 道一小时的核心实现题，每题复刻 <领域> 的一个核心机制，对照 <项目> 的固定版本。只需要 CPU。>

- 在线 / 本地浏览：打开 `index.html` · PDF：`<name>.pdf`
- `mine/` 接口骨架 · `tests/` 验收测试 · `solutions/` 带注释的参考解
- 每题的讲解与提示：`hints/<stem>.html`；领域知识：`knowledge/`

## 快速开始
    python3 -m venv .venv && .venv/bin/pip install pytest
    ./check.sh a1                # 测你写的 mine/a1_*.py
    ./check.sh a1 --solutions    # 测参考解
    ./check.sh all

## 怎么做一道题
1. 读讲解页（5–10 分钟）。2. 在 `mine/` 里实现，限时为卡片上的分钟数。
3. 跑测试；卡住 10–15 分钟再按 L1 → L2 → L3 看提示。4. 对照参考解和追问。

## 进度表
| ✓ | 编号 | 题目 | 分钟 | 难度 |
|---|----|------|-----|-----|
| ☐ | A1 | ... | 50 | 中 |

## 重新生成页面
    bash <toolkit>/run.sh build_drills.py drills.json --strict --pdf

## License
<原创内容 MIT；链接到的上游代码遵循其各自的许可证。>
```
