"""Assemble one self-contained HTML page (CSS + JS inlined; highlight.js from cdnjs, optional)."""
from __future__ import annotations

import html
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / "assets"
HLJS = ('<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>\n'
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/rust.min.js"></script>')


def nav_from_toc(toc, brand: str, brand_href: str = "#", groups_html: str = "") -> str:
    """Left sidebar: brand + optional extra html + h2/h3 links."""
    links = "\n".join(
        f'<a class="nav-l{lv}" href="#{hid}">{html.escape(t)}</a>' for lv, hid, t in toc)
    return (f'<a class="brand" href="{brand_href}">{html.escape(brand)}</a>\n{groups_html}\n{links}')


def outline_from_toc(toc, label: str) -> str:
    if not toc:
        return ""
    links = "\n".join(f'<a class="o{lv}" href="#{hid}">{html.escape(t)}</a>' for lv, hid, t in toc)
    return f'<div class="ttl">{html.escape(label)}</div>\n{links}'


def render_page(*, title: str, body: str, lang: str, nav: str = "", outline: str = "", cover: str = "",
                store_key: str = "aids", description: str = "", footer: str = "", code: bool = True,
                copied: str = "✓", theme_label: str = "Theme") -> str:
    css = (ASSETS / "site.css").read_text(encoding="utf-8")
    js = (ASSETS / "site.js").read_text(encoding="utf-8")
    layout_cls = "layout has-right" if outline else "layout"
    html_lang = "zh-CN" if lang == "zh" else "en"
    side = f'<nav class="sidebar" aria-label="nav">{nav}</nav>' if nav else '<nav class="sidebar"></nav>'
    right = f'<aside class="outline" aria-label="outline">{outline}</aside>' if outline else ""
    desc = f'<meta name="description" content="{html.escape(description)}">' if description else ""
    return f"""<!doctype html>
<html lang="{html_lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
{desc}
<style>
{css}
</style>
</head>
<body data-store="{html.escape(store_key)}" data-copied="{html.escape(copied)}">
<div class="{layout_cls}">
{side}
<main>
{cover}
{body}
{footer}
</main>
{right}
</div>
<button class="theme-btn" type="button" id="theme-btn">◐ {html.escape(theme_label)}</button>
{HLJS if code else ""}
<script>
{js}
</script>
</body>
</html>
"""
