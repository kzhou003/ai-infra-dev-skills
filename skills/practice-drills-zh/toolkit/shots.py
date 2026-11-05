"""Screenshot every diagram of a built page (3 per PNG, numbered #0, #1, ...) so you can look at each one.

    python3 shots.py page.html out_dir/

The linter in mdx.py catches overlaps and text overflow, but not crossing edges, labels sitting
on lines, or a layout that is simply hard to read. Always open the PNGs and look before you ship.
"""
from __future__ import annotations

import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_pdf import chrome_cmd  # noqa: E402
from page import render_page  # noqa: E402

PER_SHOT = 3   # diagrams stacked per screenshot (one Chrome launch each)
FIG = re.compile(r'<figure class="flow">.*?</figure>', re.S)


def shots(src: Path, out_dir: Path) -> list[Path]:
    text = Path(src).read_text(encoding="utf-8")
    lang = "zh" if 'lang="zh-CN"' in text[:300] else "en"
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("fig-*.png"):
        old.unlink()
    figs = FIG.findall(text)
    jobs = []
    for start in range(0, len(figs), PER_SHOT):
        chunk = figs[start:start + PER_SHOT]
        body = "".join(f'<div class="shot-n">#{start + j}</div>{f}' for j, f in enumerate(chunk))
        page = render_page(title=f"figs {start}", body=f'<div style="max-width:900px">{body}</div>', lang=lang, code=False)
        page = page.replace('<nav class="sidebar"></nav>', "").replace('class="layout"', 'class="solo"')
        page = page.replace("</style>", "body{background:#fff} main{padding:12px;max-width:none} .theme-btn{display:none}"
                            " .shot-n{font:700 12px monospace;color:#c0392b;margin:10px 0 -10px}"
                            " *{animation:none!important;transition:none!important}</style>", 1)
        page = page.replace("<head>", "<head>\n<script>window.__PRINT__ = true;</script>", 1)  # light theme
        html_path = out_dir / f".fig-{start:02d}.html"
        html_path.write_text(page, encoding="utf-8")
        jobs.append((html_path, out_dir / f"fig-{start:02d}-{start + len(chunk) - 1:02d}.png"))

    def run(job):
        html_path, png = job
        for _ in range(3):   # headless Chrome occasionally never exits: time out and retry
            try:
                subprocess.run(chrome_cmd("--hide-scrollbars", "--force-device-scale-factor=1", "--window-size=940,1500",
                                          "--virtual-time-budget=1500", f"--screenshot={png}", html_path.as_uri()),
                               capture_output=True, timeout=45)
            except subprocess.TimeoutExpired:
                pass
            if png.exists():
                break
        html_path.unlink(missing_ok=True)
        return png if png.exists() else None

    with ThreadPoolExecutor(4) as ex:
        paths = [p for p in ex.map(run, jobs) if p]
    return paths


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    ps = shots(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"{len(ps)} diagram screenshots in {sys.argv[2]}")
    for p in ps:
        print("  ", p)
