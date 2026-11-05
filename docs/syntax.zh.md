# 写作语法（toolkit Markdown）

页面是 CommonMark + 表格 + 原始 HTML，再加上下面这些扩展。报告、知识页、提示页都由同一个渲染器（`toolkit/mdx.py`）生成。

## 页头

知识页和提示页的开头：

```markdown
lede: 标题下方的一句话：这一页讲什么。
# 页面标题
```

报告的标题和 lede 写在 `report.json` 里，`report.md` 直接从 `## 章` 开始。`##` = 章（PDF 新起一页，进入左侧目录），`###` = 节（进入目录和右侧大纲）。

## 容器

用 `:::` 包起来，可以嵌套。扫描时会跳过代码块，所以代码里的 `:::` 是安全的。

```markdown
::: callout analogy 会“记住住客”的酒店房间        类型：analogy key info warn ok idea
正文。把映射写明白：房间 = block，住客人数 = ref_cnt。
:::

::: hint 1 I/O 示例与关键问题                      级别 1、2、3（轻度 → 重度剧透）
...
:::

::: answer 关键问题答案                            点击展开
...
:::

::: solution solutions/a1_block_pool.py            可折叠，提示“先自己写完”
{{code: solutions/a1_block_pool.py}}
:::

::: tabs
--- tab Python
...
--- tab Rust
...
:::

::: raw
<svg>...</svg>                                     原样输出
:::
```

中文页面里，类比框会自动显示为“类比 · 标题”，要点框为“要点 · 标题”，注意框为“注意 · 标题”。标题不要再重复“类比”两个字。

## 图：`::: flow`（React Flow 风格，静态 SVG）

```markdown
::: flow 两级缓存与“请求进行中”锁
cfg cw=220 rh=96 nw=164
n req 0 0 "请求 A" "缓存未命中" k=dark
n key 1 0 "路由级缓存" "key = hash(路径…)" k=teal
n lock 2 0 "claim 锁" "" k=warn w=0.8
n h 3 0 "handler 抓取" "列表页" k=pass
n det 3 1 "cache.tryGet" "每篇详情单独缓存" k=teal
e req -> key
e key -> lock "抢到锁"
e lock -> h
e h -> det "N 次" dash
g 1 0 2 0 "中间件" k=acc
cap: 路由级缓存见 [[rh:lib/middleware/cache.ts@middleware|cache.ts]]。
:::
```

| 语句 | 含义 |
|---|---|
| `cfg cw= rh= nw=` | 列宽、行高、默认节点宽度（像素）。默认 200 / 88 / 160 |
| `n id 列 行 "标题" ["副标题"] [k=类型] [w=1.3]` | 网格上的节点；列/行可以是小数（0.5、1.4）；`w` 按比例放宽 |
| 类型 | `acc` 蓝 · `vio` 紫 · `teal` 青 · `pass` 绿 · `warn` 黄 · `todo` 红 · `dark` 黑（闭源 / 外部 / 起点）· `ghost` 虚线框 |
| `e a -> b ["标签"] [k=类型] [dash] [anim]` | 带箭头的贝塞尔连线；`dash` = 可选或异步，`anim` = 流动的虚线（表示数据在流动） |
| `e a:b -> c:t` | 指定连接边：`t` 上 `b` 下 `l` 左 `r` 右（不写则按几何位置自动选） |
| `g c0 r0 c1 r1 "标签" [k=类型]` | 框住一片网格区域的虚线分组 |
| `cap: ...` | 图注，可以用行内 Markdown 和源码链接 |

**Lint（构建错误）**：要修，不要绕过：
- 节点重叠 → 挪开，或者加大 `cw`/`rh`；
- 标题或副标题超出方框 → 缩短，或加大 `w=`；
- 相邻两个节点之间放不下边标签 → 加大 `cw`（空隙 = cw − 节点宽度），把节点拉开，或者去掉标签、写进图注或副标题；
- 节点 id 不存在或重复；边标签超过几个词。

**尺寸**：可用宽度约 840 px，更宽的图会被等比缩小。预算：`列数 × cw + nw ≲ 900`。字宽估算：拉丁字符约 0.56 em，副标题等宽字体约 0.62 em，汉字约 0.92 em（标题 13 px，副标题 11 px）。所以一个 160 px 宽的节点，标题大约放 11 个汉字，副标题大约 13 个汉字。

**不容易乱的布局习惯**：主路径放第 0 行，从左到右；返回路径或存储放下面第 1 行；外部或闭源系统用 `k=dark` 放在边上。回头的连线指定连接边（`x:b -> y:b` 会在下方绕一个 U 形）。一张图最多约 10 个节点，再多就拆成两张。

## 逐步演示动画：`::: steps`

先放一张图，后面跟着若干步。每一步可以高亮节点（`{hl=a,b}`），两个都被高亮的节点之间的连线会动起来。读者可以点上一步 / 下一步、点圆点，或者点 ▶ 自动播放。打印时所有步骤都会展开。

```markdown
::: steps 4 个 block 的池子，block_size = 4
::: flow
cfg cw=150 rh=80 nw=122
n q 0 0 "空闲队列" "队头 → 队尾" k=warn
n b0 1 0 "block 0" "" k=acc
n b1 2 0 "block 1" "" k=acc
e q -> b0
e b0 -> b1 dash
:::
--- step 初始状态 {hl=q,b0,b1}
全部空闲：{{cells: on:0 on:1 _:2 _:3}}
--- step allocate(10 个 token) {hl=b0,b1}
正文、代码、表格都可以。
:::
```

每一步里的所有数字都要**运行参考实现得出**，不要手算。

## 行内宏

| 宏 | 渲染结果 |
|---|---|
| `{{cells: t:1 h:2 on:3 bad:x ok:✓ gap:· _:4}}` | 一行彩色格子（数组状态、队列内容）。类：`t` 蓝、`h` 紫、`w` 青、`on` 高亮、`off` 变淡、`ok`、`bad`、`gap` 虚线、`_` 无样式 |
| `{{code: path/to/file.py}}`（单独一行） | 嵌入本项目文件：带高亮和复制按钮的代码块；`#L10-L40` 只嵌入一段 |

## 固定版本的源码链接

在配置文件（`report.json` / `drills.json`）里声明仓库：

```json
"pins": {
  "vllm": {"repo": "vllm-project/vllm", "sha": "5e65d6b2adf64d1548c3b25ccc52ad55fcfe8044", "local": "~/development/vllm"}
}
```

`local` 可选。有它时用 `git show <sha>:<path>` 读文件，所以工作区改过、切到别的分支都没关系。没有它时走 GitHub API 和 raw 文件，缓存在 `.cache/sources/`（限流时设置 `GITHUB_TOKEN`）。

| 宏 | 链接到 |
|---|---|
| `[[vllm:vllm/v1/core/block_pool.py]]` | 固定 SHA 下的文件 |
| `[[vllm:vllm/v1/core/block_pool.py#L347]]` / `#L347-L360` | 一行 / 一段（会检查是否超过文件长度） |
| `[[vllm:vllm/v1/core/block_pool.py@BlockPool.touch\|touch]]` | `BlockPool` 里定义 `touch` 的那一行，自定义标签 |
| `[[vllm:vllm/v1/core/]]` | 目录（tree 视图） |
| `[[vllm]]` | 固定 SHA 下的仓库根目录 |
| `[[here:solutions/a1.py\|标签]]` | 本项目里的文件（相对链接） |

所有宏都在构建时解析。路径不存在、行号超过文件末尾、找不到符号，都是构建错误，所以死链接不会发布出去。`@Symbol` 的查找顺序：先找 `def/class/fn/struct/function/const …` 定义，再找 `name =`/`name(`，最后找整词匹配；`A.b` 表示在 `A` 之后找 `b`。
