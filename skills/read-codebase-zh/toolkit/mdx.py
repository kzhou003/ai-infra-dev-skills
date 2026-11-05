"""Markdown with containers, diagrams and pinned source links -> HTML fragments.

CommonMark + tables + raw HTML, plus fenced containers (nesting allowed; fenced code is skipped):

    ::: callout analogy Title     boxed note. kinds: analogy | key | info | warn | ok | idea
    ::: hint 1 Title              collapsible hint, level 1..3 (light / medium / heavy spoiler)
    ::: answer Title              click-to-reveal answer
    ::: solution Title            collapsible reference solution ("write yours first")
    ::: flow Title                React-Flow-style node diagram (DSL below)
    ::: steps Title               step-through animation; content before the first `--- step`
    --- step Title {hl=a,b}       (e.g. a nested ::: flow) is the shared diagram, `hl` highlights
                                  those node ids in it while the step is shown
    ::: tabs                      tabbed panes, each starts with `--- tab Label`
    ::: raw                       emitted verbatim (inline SVG etc.)
    :::                           closes the innermost container

Line macros:
    {{code: path/to/file.py [title]}}     embed a project file as a highlighted, copyable block
    {{code: path/to/file.py#L10-L40 [title]}}
Inline macros:
    [[alias:path#L1-L9|label]] ...        pinned source link (see pins.py)
    {{cells: t:1 h:2 w+on:3 bad:x _:·}}   a row of coloured cells (t h w on off ok bad gap)

Flow DSL (one statement per line):
    cfg cw=200 rh=90 nw=160               column width, row height, default node width (px)
    n id col row "title" ["sub"] [k=acc] [w=1.3]
                                          kinds: acc vio teal pass warn todo dark ghost
    e a[:side] -> b[:side] ["label"] [k=acc] [anim] [dash]   side: t b l r (auto if omitted)
    g c0 r0 c1 r1 "label" [k=acc]         dashed group box around a grid range
    cap: caption (inline markdown + source links allowed)

The flow linter rejects overlapping nodes, titles / subtitles wider than their box, unknown node
ids and duplicate ids, so diagrams cannot silently render broken. Edge crossings are not detected:
look at the screenshots (shots.py).
"""
from __future__ import annotations

import html
import json
import re
import shlex
from pathlib import Path

from markdown_it import MarkdownIt

from pins import MACRO, Pins

I18N = {
    "zh": {
        "hover": "悬停节点查看连接", "prev": "← 上一步", "next": "下一步 →", "play": "▶ 自动播放", "pause": "❚❚ 暂停",
        "hint": {"1": "方向（轻度剧透）", "2": "拆解与常见坑（中度剧透）", "3": "几乎是答案（重度剧透）"},
        "answer": "显示答案", "solution": "参考解", "solution_note": "先自己写完、跑过测试再看",
        "callout": {"analogy": "类比", "key": "要点", "warn": "注意", "info": "", "ok": "", "idea": "想一想"},
        "copy": "复制", "copied": "已复制", "lines": "行", "toc": "目录", "theme": "主题", "outline": "本页内容",
        "minutes": "分钟", "step": "步",
    },
    "en": {
        "hover": "hover a node to see its connections", "prev": "← Prev", "next": "Next →", "play": "▶ Play",
        "pause": "❚❚ Pause",
        "hint": {"1": "direction (light spoiler)", "2": "breakdown & pitfalls (medium spoiler)",
                 "3": "nearly the answer (heavy spoiler)"},
        "answer": "Show answer", "solution": "Reference solution", "solution_note": "finish and test yours first",
        "callout": {"analogy": "Analogy", "key": "Key point", "warn": "Watch out", "info": "", "ok": "",
                    "idea": "Think about it"},
        "copy": "Copy", "copied": "Copied", "lines": "lines", "toc": "Contents", "theme": "Theme",
        "outline": "On this page", "minutes": "min", "step": "step",
    },
}

MD = MarkdownIt("commonmark", {"html": True, "typographer": False}).enable(["table", "strikethrough"])
OPEN_RE = re.compile(r"^:::\s*(\w+)\s*(.*)$")
CLOSE_RE = re.compile(r"^:::\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
STEP_RE = re.compile(r"^---\s*step\s+(.*?)\s*(?:\{hl=([^}]*)\})?\s*$")
TAB_RE = re.compile(r"^---\s*tab\s+(.*?)\s*$")
CODE_RE = re.compile(r"^\{\{code:\s*([^\s#]+)(?:#L(\d+)(?:-L(\d+))?)?\s*(.*?)\}\}\s*$")
CELLS_RE = re.compile(r"\{\{cells:\s*(.*?)\}\}")
LANG = {".py": "python", ".cu": "cpp", ".cuh": "cpp", ".cc": "cpp", ".cpp": "cpp", ".h": "cpp", ".hpp": "cpp",
        ".sh": "bash", ".rs": "rust", ".ts": "typescript", ".tsx": "typescript", ".js": "javascript",
        ".go": "go", ".java": "java", ".toml": "ini", ".yaml": "yaml", ".yml": "yaml", ".json": "json",
        ".mlir": "plaintext", ".ll": "llvm", ".md": "markdown"}


def text_w(s: str, size: float, mono: bool = False) -> float:
    """Rough rendered width of a label (CJK ≈ 0.92 em; latin ≈ 0.56 em, monospace ≈ 0.62 em)."""
    latin = 0.62 if mono else 0.56
    return sum(size * (0.92 if ord(c) > 0x2E7F else latin) for c in s)


class Renderer:
    def __init__(self, lang: str = "zh", pins: Pins | None = None, project_root: Path | None = None,
                 here_prefix: str = ""):
        self.lang = lang if lang in I18N else "en"
        self.t = I18N[self.lang]
        self.pins = pins
        self.root = Path(project_root or ".")
        self.here_prefix = here_prefix
        self.errors: list[str] = []
        self.stats = {"flows": 0, "steps": 0, "analogies": 0, "hints": 0, "code": 0}

    # ---------- inline ----------
    def inline_macros(self, text: str) -> str:
        """Source links + cells, applied outside fenced code and inline code spans."""
        out, in_fence = [], False
        for line in text.split("\n"):
            if FENCE_RE.match(line):
                in_fence = not in_fence
                out.append(line)
                continue
            if in_fence:
                out.append(line)
                continue
            parts = re.split(r"(`[^`]*`)", line)
            for i in range(0, len(parts), 2):
                parts[i] = MACRO.sub(self._link, parts[i])
                parts[i] = CELLS_RE.sub(self._cells, parts[i])
            out.append("".join(parts))
        return "\n".join(out)

    def _link(self, m):
        if self.pins is None:
            self.errors.append(f"source link {m.group(0)} but no pins configured")
            return m.group(0)
        href, label = self.pins.resolve(m, self.here_prefix, self.root)
        return f'<a class="src" href="{html.escape(href)}">{html.escape(label)}</a>'

    @staticmethod
    def _cells(m):
        out = []
        for tok in m.group(1).split():
            cls, sep, text = tok.partition(":")
            if not sep:
                cls, text = "_", tok
            classes = " ".join(c for c in cls.split("+") if c != "_")
            out.append(f'<span class="cell {classes}">{html.escape(text)}</span>')
        return f'<span class="cells">{"".join(out)}</span>'

    def md(self, text: str) -> str:
        out = MD.render(self.inline_macros(text))
        return out.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")

    def md_inline(self, text: str) -> str:
        return MD.renderInline(self.inline_macros(text))

    # ---------- blocks ----------
    @staticmethod
    def split_blocks(lines):
        out, i, in_fence = [], 0, False
        while i < len(lines):
            line = lines[i]
            if FENCE_RE.match(line):
                in_fence = not in_fence
                out.append(line)
                i += 1
                continue
            m = None if in_fence else OPEN_RE.match(line)
            if not m:
                out.append(line)
                i += 1
                continue
            depth, j, inner, f = 1, i + 1, [], False
            while j < len(lines):
                ln = lines[j]
                if FENCE_RE.match(ln):
                    f = not f
                elif not f and OPEN_RE.match(ln):
                    depth += 1
                elif not f and CLOSE_RE.match(ln):
                    depth -= 1
                    if depth == 0:
                        break
                inner.append(ln)
                j += 1
            if depth:
                raise SystemExit(f"unclosed ::: {m.group(1)} near: {line!r}")
            out.append((m.group(1), m.group(2).strip(), inner))
            i = j + 1
        return out

    def render(self, lines) -> str:
        if isinstance(lines, str):
            lines = lines.split("\n")
        parts, buf = [], []

        def flush():
            if buf:
                parts.append(self.md("\n".join(buf)))
                buf.clear()

        for b in self.split_blocks(lines):
            if isinstance(b, str):
                m = CODE_RE.match(b)
                if m:
                    flush()
                    parts.append(self.code_block(*m.groups()))
                else:
                    buf.append(b)
                continue
            flush()
            name, args, inner = b
            parts.append(self.container(name, args, inner))
        flush()
        return "\n".join(parts)

    def container(self, name, args, inner):
        t = self.t
        if name == "raw":
            return "\n".join(inner)
        if name == "callout":
            kind, _, title = args.partition(" ")
            if kind == "analogy":
                self.stats["analogies"] += 1
            label = t["callout"].get(kind, "")
            # "Analogy · Title"; never "Analogy · Analogy"
            if label and title and title.lower() != label.lower():
                head = f"{label} · {title}"
            else:
                head = title or label
            h = f'<div class="callout-title">{html.escape(head)}</div>' if head else ""
            return f'<div class="callout {kind}">{h}{self.render(inner)}</div>'
        if name == "hint":
            self.stats["hints"] += 1
            lvl, _, title = args.partition(" ")
            return (f'<details class="hint l{lvl}"><summary><span class="lvl">L{lvl}</span>{html.escape(title)}'
                    f'<span class="spoiler-note">{t["hint"].get(lvl, "")}</span></summary>'
                    f'<div class="body">{self.render(inner)}</div></details>')
        if name == "answer":
            return (f'<details class="answer"><summary>{html.escape(args or t["answer"])}</summary>'
                    f'<div class="body">{self.render(inner)}</div></details>')
        if name == "solution":
            return (f'<details class="solution"><summary><span class="lvl">✓</span>{html.escape(args or t["solution"])}'
                    f'<span class="spoiler-note">{t["solution_note"]}</span></summary>'
                    f'<div class="body">{self.render(inner)}</div></details>')
        if name == "flow":
            return self.flow(args, inner)
        if name == "steps":
            return self.steps(args, inner)
        if name == "tabs":
            return self.tabs(inner)
        raise SystemExit(f"unknown container ::: {name}")

    def code_block(self, path, l0, l1, title):
        p = self.root / path
        if not p.exists():
            self.errors.append(f"{{{{code: {path}}}}}: file not found")
            return ""
        self.stats["code"] += 1
        lines = p.read_text(encoding="utf-8").rstrip("\n").split("\n")
        first = 1
        if l0:
            first, last = int(l0), int(l1 or l0)
            lines = lines[first - 1:last]
        text = "\n".join(lines)
        lang = LANG.get(p.suffix, "plaintext")
        label = html.escape(title or path + (f":{l0}-{l1}" if l0 else ""))
        return (f'<div class="codebox"><div class="code-head"><span class="path">{label}</span>'
                f'<span class="muted small">{len(lines)} {self.t["lines"]}</span>'
                f'<button type="button" class="btn copy">{self.t["copy"]}</button></div>'
                f'<pre><code class="language-{lang}">{html.escape(text)}</code></pre></div>')

    def tabs(self, inner):
        panes, cur = [], None
        for ln in inner:
            m = TAB_RE.match(ln)
            if m:
                cur = (m.group(1), [])
                panes.append(cur)
            elif cur is not None:
                cur[1].append(ln)
        heads = "".join(f'<button type="button" class="tab-btn{" on" if i == 0 else ""}">{html.escape(n)}</button>'
                        for i, (n, _) in enumerate(panes))
        bodies = "".join(f'<div class="tab-pane{" on" if i == 0 else ""}">{self.render(ls)}</div>'
                         for i, (_, ls) in enumerate(panes))
        return f'<div class="tabs"><div class="tab-heads">{heads}</div>{bodies}</div>'

    def steps(self, title, inner):
        self.stats["steps"] += 1
        pre, steps, cur = [], [], None
        for ln in inner:
            m = STEP_RE.match(ln)
            if m:
                cur = (m.group(1), m.group(2) or "", [])
                steps.append(cur)
            elif cur is None:
                pre.append(ln)
            else:
                cur[2].append(ln)
        if not steps:
            self.errors.append(f"steps {title!r}: no `--- step` lines")
        dia = self.render(pre).strip()
        dia = f'<div class="st-diagram">{dia}</div>' if dia else ""
        body = "".join(
            f'<div class="step" data-hl="{html.escape(hl)}"><div class="step-title">{i + 1}. {html.escape(st)}</div>'
            f'{self.render(ls)}</div>' for i, (st, hl, ls) in enumerate(steps))
        t = self.t
        return (f'<div class="stepper"><div class="st-head"><span class="st-title">▶ {html.escape(title)}</span>'
                f'<span class="st-count"></span><span class="st-ctrl">'
                f'<button type="button" class="btn st-play" data-play="{t["play"]}" data-pause="{t["pause"]}">{t["play"]}</button>'
                f'<button type="button" class="btn st-prev">{t["prev"]}</button>'
                f'<button type="button" class="btn primary st-next">{t["next"]}</button></span></div>'
                f'<div class="st-dots"></div>{dia}<div class="st-body">{body}</div></div>')

    # ---------- flow diagrams ----------
    def flow(self, title, lines):
        self.stats["flows"] += 1
        spec = {"title": title, "nodes": [], "edges": [], "groups": [], "cfg": {}}
        caption = ""
        is_opt = lambda tk: re.fullmatch(r"(k|w|cw|rh|nw)=\S+", tk) is not None
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("cap:"):
                caption = line[4:].strip()
                continue
            try:
                tok = shlex.split(line)
            except ValueError as e:
                self.errors.append(f"flow {title!r}: {e}: {line!r}")
                continue
            kind, rest = tok[0], tok[1:]
            opts = {k: v for k, _, v in (x.partition("=") for x in rest if is_opt(x))}
            flags = {x for x in rest if not is_opt(x)}
            if kind == "cfg":
                spec["cfg"] = {k: float(v) for k, v in opts.items()}
            elif kind == "n":
                nid, c, r = rest[0], float(rest[1]), float(rest[2])
                texts = [x for x in rest[3:] if not is_opt(x)]
                spec["nodes"].append({"id": nid, "c": c, "r": r, "t": texts[0] if texts else nid,
                                      "s": texts[1] if len(texts) > 1 else "", "k": opts.get("k", ""),
                                      "w": float(opts.get("w", 1))})
            elif kind == "e":
                if len(rest) < 3 or rest[1] != "->":
                    self.errors.append(f"flow {title!r}: bad edge {line!r}")
                    continue
                texts = [x for x in rest[3:] if not is_opt(x) and x not in ("anim", "dash")]
                spec["edges"].append({"a": rest[0], "b": rest[2], "t": texts[0] if texts else "",
                                      "k": opts.get("k", ""), "anim": "anim" in flags, "dash": "dash" in flags})
            elif kind == "g":
                c0, r0, c1, r1 = map(float, rest[:4])
                texts = [x for x in rest[4:] if not is_opt(x)]
                spec["groups"].append({"c0": c0, "r0": r0, "c1": c1, "r1": r1, "t": texts[0] if texts else "",
                                       "k": opts.get("k", "")})
            else:
                self.errors.append(f"flow {title!r}: unknown statement {line!r}")
        self.lint_flow(title, spec)
        cap = self.md_inline(caption) if caption else ""
        head = (f'<div class="flow-head">{html.escape(title)}<span class="flow-hint">{self.t["hover"]}</span></div>'
                if title else "")
        return (f'<figure class="flow">{head}'
                f'<div class="flow-body" data-flow="{html.escape(json.dumps(spec, ensure_ascii=False))}"></div>'
                + (f"<figcaption>{cap}</figcaption>" if cap else "") + "</figure>")

    def lint_flow(self, title, spec):
        cw, rh, nw = spec["cfg"].get("cw", 200), spec["cfg"].get("rh", 88), spec["cfg"].get("nw", 160)
        ids, boxes = set(), []
        for n in spec["nodes"]:
            if n["id"] in ids:
                self.errors.append(f"flow {title!r}: duplicate node id {n['id']!r}")
            ids.add(n["id"])
            w = nw * n["w"]
            if text_w(n["t"], 13) > w - 14:
                self.errors.append(f"flow {title!r}: title of {n['id']!r} is too wide "
                                   f"({text_w(n['t'], 13):.0f}px > {w - 14:.0f}px): shorten it or raise w=")
            if n["s"] and text_w(n["s"], 11, mono=True) > w - 12:
                self.errors.append(f"flow {title!r}: subtitle of {n['id']!r} is too wide "
                                   f"({text_w(n['s'], 11, mono=True):.0f}px > {w - 12:.0f}px): shorten it or raise w=")
            boxes.append((n["id"], n["c"] * cw, n["r"] * rh, n["c"] * cw + w, n["r"] * rh + (52 if n["s"] else 38)))
        for i, a in enumerate(boxes):
            for b in boxes[i + 1:]:
                if a[1] < b[3] + 12 and b[1] < a[3] + 12 and a[2] < b[4] + 8 and b[2] < a[4] + 8:
                    self.errors.append(f"flow {title!r}: nodes {a[0]!r} and {b[0]!r} overlap")
        box = {b[0]: b for b in boxes}
        for e in spec["edges"]:
            ends = [x.split(":") for x in (e["a"], e["b"])]
            if any(x[0] not in ids for x in ends):
                for x in ends:
                    if x[0] not in ids:
                        self.errors.append(f"flow {title!r}: edge to unknown node {x[0]!r}")
                continue
            if not e["t"]:
                continue
            lw = text_w(e["t"], 11, mono=True) + 16
            if lw > 160:
                self.errors.append(f"flow {title!r}: edge label {e['t']!r} is long; keep it to a few words")
            # Will the label fit in the gap between the two boxes? (mirrors the placement in site.js)
            a, b = box[ends[0][0]], box[ends[1][0]]
            dx = (b[1] + b[3]) / 2 - (a[1] + a[3]) / 2
            dy = (b[2] + b[4]) / 2 - (a[2] + a[4]) / 2
            sides = (ends[0][1] if len(ends[0]) > 1 else None, ends[1][1] if len(ends[1]) > 1 else None)
            horiz = (abs(dx) >= abs(dy) * 0.9) if sides == (None, None) else all(s in ("l", "r", None) for s in sides)
            if horiz and abs(dy) < 30:
                gap = (b[1] - a[3]) if dx > 0 else (a[1] - b[3])
                if 0 <= gap < lw + 10:
                    self.errors.append(f"flow {title!r}: label {e['t']!r} ({lw:.0f}px) does not fit the {gap:.0f}px gap "
                                       f"between {ends[0][0]!r} and {ends[1][0]!r}; raise cw, move a node, or drop the label")
            elif not horiz and abs(dx) < 30:
                gap = (b[2] - a[4]) if dy > 0 else (a[2] - b[4])
                if 0 <= gap < 30:
                    self.errors.append(f"flow {title!r}: label {e['t']!r} has no room in the {gap:.0f}px vertical gap "
                                       f"between {ends[0][0]!r} and {ends[1][0]!r}; raise rh or drop the label")


def read_page(path: Path):
    """A source page: first line `lede: ...`, optional `# Title` next. -> (lede, title, lines)."""
    lines = path.read_text(encoding="utf-8").split("\n")
    lede, title = "", ""
    if lines and lines[0].startswith("lede:"):
        lede, lines = lines[0][5:].strip(), lines[1:]
    while lines and not lines[0].strip():
        lines = lines[1:]
    if lines and lines[0].startswith("# "):
        title, lines = lines[0][2:].strip(), lines[1:]
    return lede, title, lines


def heading_ids(body: str, prefix: str = "s"):
    """Give h2/h3 stable ids; -> (body, [(level, id, text)])."""
    toc, n = [], [0, 0]

    def sub(m):
        level, attrs, inner = m.group(1), m.group(2), m.group(3)
        plain = html.unescape(re.sub(r"<[^>]+>", "", inner))
        if level == "2":
            n[0] += 1
            n[1] = 0
            hid = f"{prefix}{n[0]}"
        else:
            n[1] += 1
            hid = f"{prefix}{n[0]}-{n[1]}"
        toc.append((level, hid, plain))
        return f'<h{level} id="{hid}"{attrs}>{inner}</h{level}>'

    return re.sub(r"<h([23])((?:\s[^>]*)?)>(.*?)</h\1>", sub, body), toc
