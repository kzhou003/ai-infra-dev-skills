# Authoring syntax (toolkit Markdown)

Pages are CommonMark + tables + raw HTML, plus the extensions below. The same renderer (`toolkit/mdx.py`) builds reports, knowledge pages and hint pages.

## Page header

Knowledge and hint pages start with:

```markdown
lede: One sentence shown under the title: what this page explains.
# Page title
```

A report's title and lede live in `report.json` instead; `report.md` starts directly with `## Chapter`. `##` = chapter (new PDF page, left nav), `###` = section (nav + right outline).

## Containers

Fenced with `:::`, nestable. Fenced code blocks are skipped when scanning, so `:::` inside code is safe.

```markdown
::: callout analogy Hotel rooms with a memory       kinds: analogy key info warn ok idea
Body. Make the mapping explicit: room = block, guest count = ref_cnt.
:::

::: hint 1 I/O examples and key questions           level 1, 2 or 3 (light → heavy spoiler)
...
:::

::: answer Answers to the key questions             click to reveal
...
:::

::: solution solutions/a1_block_pool.py             collapsible "write yours first"
{{code: solutions/a1_block_pool.py}}
:::

::: tabs
--- tab Python
...
--- tab Rust
...
:::

::: raw
<svg>...</svg>                                       emitted verbatim
:::
```

## Diagrams: `::: flow` (React Flow style, static SVG)

```markdown
::: flow Two-level cache with an in-flight lock
cfg cw=200 rh=96 nw=164
n req 0 0 "request A" "cache miss" k=dark
n key 1 0 "route cache" "key = hash(path…)" k=teal
n lock 2 0 "claim lock" "" k=warn w=0.8
n h 3 0 "handler" "fetch list page" k=pass
n det 3 1 "cache.tryGet" "per-item cache" k=teal
e req -> key
e key -> lock "won"
e lock -> h
e h -> det "N times" dash
e det:l -> key:b "next request" anim
g 1 0 2 0 "middleware" k=acc
cap: Route cache in [[rh:lib/middleware/cache.ts@middleware|cache.ts]]; item cache via `cache.tryGet`.
:::
```

| Statement | Meaning |
|---|---|
| `cfg cw= rh= nw=` | column width, row height, default node width (px). Defaults 200 / 88 / 160 |
| `n id col row "title" ["subtitle"] [k=kind] [w=1.3]` | node on a grid; `col`/`row` may be fractional (0.5, 1.4); `w` scales the width |
| kinds | `acc` (blue) `vio` (purple) `teal` `pass` (green) `warn` (amber) `todo` (red) `dark` (closed / external / start) `ghost` (dashed outline) |
| `e a -> b ["label"] [k=kind] [dash] [anim]` | bezier edge with arrowhead; `dash` = optional or async, `anim` = moving dashes (data flowing) |
| `e a:b -> c:t` | force sides: `t` `b` `l` `r` (auto picks by geometry) |
| `g c0 r0 c1 r1 "label" [k=kind]` | dashed group box around a grid range |
| `cap: ...` | caption; inline Markdown and source links allowed |

**Lint (build errors).** Fix them, don't suppress them:
- nodes overlap → move one, or raise `cw`/`rh`;
- title or subtitle wider than its box → shorten it or raise `w=`;
- an edge label doesn't fit the gap between two adjacent nodes → raise `cw` (gap = cw − node width), move the nodes apart, or drop the label and say it in the caption or subtitle;
- unknown or duplicate node id; edge label longer than a few words.

**Sizing.** About 840 px of width is available; wider diagrams are scaled down. Budget: `cols × cw + nw ≲ 900`. Roughly 0.56 em per Latin character, 0.62 em for the monospace subtitle and 0.92 em for CJK (13 px titles, 11 px subtitles).

**Layout habits that stay clean.** Main path left → right on row 0; return path or storage on row 1 below; external or closed systems as `k=dark` at the edges. Use explicit sides for back-edges (`x:b -> y:b` makes a U-turn under the row). At most ~10 nodes per diagram: split instead.

## Step-through animations: `::: steps`

A diagram followed by steps. Each step can highlight node ids (`{hl=a,b}`); edges between two highlighted nodes animate. Readers click Prev/Next, the dots, or ▶ Play (auto-advance). In print, every step is shown.

```markdown
::: steps Pool of 4 blocks, block_size 4
::: flow
cfg cw=150 rh=80 nw=122
n q 0 0 "free queue" "front → back" k=warn
n b0 1 0 "block 0" "" k=acc
n b1 2 0 "block 1" "" k=acc
e q -> b0
e b0 -> b1 dash
:::
--- step Start {hl=q,b0,b1}
All blocks free: {{cells: on:0 on:1 _:2 _:3}}
--- step allocate(10 tokens) {hl=b0,b1}
Text, code, tables, anything.
:::
```

Compute every number in a step by **running the reference implementation**, never by hand.

## Inline macros

| Macro | Renders |
|---|---|
| `{{cells: t:1 h:2 on:3 bad:x ok:✓ gap:· _:4}}` | a row of coloured cells (array state, queue contents). Classes: `t` blue, `h` purple, `w` teal, `on` highlighted, `off` faded, `ok`, `bad`, `gap` dashed, `_` plain |
| `{{code: path/to/file.py}}` (own line) | the project file as a highlighted block with a copy button; `#L10-L40` for a range |

## Pinned source links

Declare repositories in the config (`report.json` / `drills.json`):

```json
"pins": {
  "vllm": {"repo": "vllm-project/vllm", "sha": "5e65d6b2adf64d1548c3b25ccc52ad55fcfe8044", "local": "~/development/vllm"}
}
```

`local` is optional. With it, files are read via `git show <sha>:<path>`, so the working tree may be modified or checked out elsewhere. Without it, the GitHub API and raw files are used and cached in `.cache/sources/` (set `GITHUB_TOKEN` for rate limits).

| Macro | Links to |
|---|---|
| `[[vllm:vllm/v1/core/block_pool.py]]` | the file at the pinned SHA |
| `[[vllm:vllm/v1/core/block_pool.py#L347]]` / `#L347-L360` | a line / range (checked against the file length) |
| `[[vllm:vllm/v1/core/block_pool.py@BlockPool.touch\|touch]]` | the line defining `touch` inside `BlockPool`, custom label |
| `[[vllm:vllm/v1/core/]]` | directory (tree view) |
| `[[vllm]]` | repo root at the SHA |
| `[[here:solutions/a1.py\|label]]` | a file of this project (relative link) |

Every macro is resolved at build time. A missing path, a line past EOF, or a symbol not found is a build error, so dead links can't ship. `@Symbol` finds `def/class/fn/struct/function/const …` definitions first, then `name =`/`name(`, then any whole-word match; `A.b` searches for `b` after `A`.
