"""Build a code-wiki style codebase report: one self-contained HTML page (+ optional PDF).

    python3 build_report.py path/to/report.json [--pdf] [--shots] [--links] [--strict]

report.json (paths relative to it):
    {
      "title": "RSSHub + Folo: from principles to source",
      "kicker": "Source-level guide",            // small caps line above the title
      "lede": "One paragraph: who this is for and what they will be able to do.",
      "lang": "en",                               // "en" | "zh" (UI strings)
      "sources": ["report.md"],                   // concatenated in order; `## ` = chapter
      "output": "report.html",
      "pdf": "report.pdf",
      "pins": {"rsshub": {"repo": "DIYgod/RSSHub", "sha": "8f4fd43...", "local": "~/development/RSSHub"}},
      "quality": {"flows": 8, "analogies": 3, "links": 40}   // minimums; --strict turns misses into errors
    }

--pdf    also print <pdf> with headless Chrome        --shots  screenshot every diagram into .shots/
--links  check every external link answers 200        --strict quality minimums are errors
Exits 1 on any unresolved source link, diagram lint error or (with --strict) unmet minimum.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mdx import I18N, Renderer, heading_ids  # noqa: E402
from page import nav_from_toc, outline_from_toc, render_page  # noqa: E402
from pins import Pins  # noqa: E402

DEFAULT_QUALITY = {"flows": 6, "analogies": 2, "links": 30}


def build(cfg_path: Path, *, pdf=False, shots=False, links=False, strict=False) -> int:
    cfg_path = Path(cfg_path).resolve()
    root = cfg_path.parent
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    lang = cfg.get("lang", "en")
    pins = Pins(cfg.get("pins", {}), root)
    r = Renderer(lang, pins, root)
    src = []
    for s in cfg.get("sources", ["report.md"]):
        src += (root / s).read_text(encoding="utf-8").split("\n") + [""]
    body, toc = heading_ids(r.render(src))
    errors = r.errors + pins.errors
    t = I18N[r.lang]

    meta = cfg.get("meta") or " · ".join(f'{p["repo"]} @ {p["sha"][:7]}' for p in cfg.get("pins", {}).values())
    cover = (f'<header class="cover"><div class="kicker">{html.escape(cfg.get("kicker", ""))}</div>'
             f'<h1>{html.escape(cfg["title"])}</h1>'
             + (f'<p class="lede">{r.md_inline(cfg["lede"])}</p>' if cfg.get("lede") else "")
             + (f'<p class="meta">{html.escape(meta)}</p>' if meta else "") + "</header>")
    nav = nav_from_toc(toc, cfg.get("brand", cfg["title"]))
    out = root / cfg.get("output", "report.html")
    out.write_text(render_page(title=cfg["title"], body=body, lang=lang, nav=nav, cover=cover,
                               store_key="report:" + cfg["title"][:40], description=cfg.get("lede", ""),
                               copied=t["copied"], theme_label=t["theme"]), encoding="utf-8")

    q = {**DEFAULT_QUALITY, **cfg.get("quality", {})}
    got = {"flows": r.stats["flows"], "analogies": r.stats["analogies"], "links": pins.count}
    misses = [f"quality: {k} = {got[k]} < {q[k]}" for k in q if k in got and got[k] < q[k]]
    print(f"built {out.name}: {len(toc)} headings · {got['flows']} diagrams · {r.stats['steps']} steppers · "
          f"{got['analogies']} analogies · {got['links']} source links")
    for m in misses:
        print(("ERROR " if strict else "warn  ") + m)
    for e in errors:
        print("ERROR " + e)
    if errors or (strict and misses):
        return 1
    if shots:
        from shots import shots as do_shots
        ps = do_shots(out, root / ".shots")
        print(f"{len(ps)} diagram screenshots in {root / '.shots'} — open and look at every one")
    if links:
        from check_links import main as check
        if check([out]):
            return 1
    if pdf:
        from make_pdf import make_pdf, page_count
        p = make_pdf(out, root / cfg.get("pdf", out.with_suffix(".pdf").name))
        print(f"wrote {p.name} · {page_count(p)} pages · {p.stat().st_size // 1024} KB")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    flags = set(a for a in sys.argv[1:] if a.startswith("--"))
    sys.exit(build(Path(args[0]), pdf="--pdf" in flags, shots="--shots" in flags, links="--links" in flags,
                   strict="--strict" in flags))
