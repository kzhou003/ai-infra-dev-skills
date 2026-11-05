"""Check that every external http(s) link in built HTML pages answers 200.

    python3 check_links.py page.html [more.html ...]

Pinned GitHub links are checked per file (the #L anchor is dropped). Exit code 1 if any link fails.
"""
from __future__ import annotations

import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SKIP = ("cdnjs.cloudflare.com", "fonts.googleapis.com")


def collect(paths):
    urls = set()
    for p in paths:
        for u in re.findall(r'href="(https?://[^"]+)"', Path(p).read_text(encoding="utf-8")):
            u = u.replace("&amp;", "&").split("#")[0]
            if not any(s in u for s in SKIP):
                urls.add(u)
    return sorted(urls)


def status(u):
    r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-L", "--max-time", "25", "-A", "Mozilla/5.0 (link checker)",
                        "-w", "%{http_code}", u], capture_output=True, text=True)
    return u, r.stdout.strip()


def main(paths):
    urls = collect(paths)
    bad = []
    with ThreadPoolExecutor(10) as ex:
        for u, code in ex.map(status, urls):
            if code != "200":
                bad.append((code, u))
    for code, u in bad:
        print(f"BAD {code}  {u}")
    print(f"{len(urls)} unique external links, {len(bad)} not 200")
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1:]))
