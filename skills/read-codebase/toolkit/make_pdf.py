"""Print a built page to PDF with headless Chrome (no Node / Playwright needed).

    python3 make_pdf.py page.html out.pdf

The page is printed in "print mode": light theme, every <details> (hints, answers, solutions)
opened, every stepper step shown, navigation hidden, one chapter (h2) per page.
Set CHROME=/path/to/chrome if Chrome is not found automatically.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]


def chrome() -> str:
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    for c in CANDIDATES:
        if Path(c).exists():
            return c
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        p = shutil.which(name)
        if p:
            return p
    raise SystemExit("Chrome/Chromium not found; set CHROME=/path/to/chrome")


def chrome_cmd(*extra: str) -> list[str]:
    """Headless Chrome with a throwaway profile (the default profile adds seconds of start-up work)."""
    prof = tempfile.mkdtemp(prefix="aids-chrome-")
    return [chrome(), "--headless=new", "--disable-gpu", f"--user-data-dir={prof}", "--no-first-run",
            "--no-default-browser-check", "--disable-extensions", "--disable-component-update", "--disable-sync",
            "--disable-background-networking", *extra]


PRINT_HEAD = """<script>window.__PRINT__ = true;</script>
<style>@page { size: A4; margin: 13mm 12mm 14mm; }
*, *::before, *::after { animation: none !important; transition: none !important; }</style>
"""


def make_pdf(src: Path, out: Path, budget_ms: int = 5000) -> Path:
    src, out = Path(src).resolve(), Path(out).resolve()
    tmp = src.with_name(f".print-{src.name}")
    text = src.read_text(encoding="utf-8")
    tmp.write_text(text.replace("<head>", "<head>\n" + PRINT_HEAD, 1), encoding="utf-8")
    try:
        r = subprocess.run(chrome_cmd("--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
                                      f"--virtual-time-budget={budget_ms}", f"--print-to-pdf={out}", tmp.as_uri()),
                           capture_output=True, text=True, timeout=240)
        if r.returncode != 0 or not out.exists():
            raise SystemExit(f"chrome failed ({r.returncode}): {r.stderr[-800:]}")
    finally:
        tmp.unlink(missing_ok=True)
    return out


def page_count(pdf: Path) -> int:
    import re
    return len(re.findall(rb"/Type\s*/Page[^s]", Path(pdf).read_bytes()))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    p = make_pdf(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"wrote {p} · {page_count(p)} pages · {p.stat().st_size // 1024} KB")
