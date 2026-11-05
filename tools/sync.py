"""Copy the shared toolkit, syntax docs and examples into every skill folder.

    python3 tools/sync.py           # write the copies
    python3 tools/sync.py --check   # exit 1 if any copy is out of date (run before committing)

Each skill must be self-contained once installed (~/.claude/skills/<name>/ may be a copy, not a
symlink into this repo), so the canonical sources below are duplicated into each skill:

    toolkit/                         -> skills/<skill>/toolkit/
    docs/syntax.<lang>.md            -> skills/<skill>/reference/syntax.md
    examples/<example>/ (sources)    -> skills/<skill>/examples/<short>/
"""
from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IGNORE = shutil.ignore_patterns("__pycache__", ".cache", ".shots", "*.pyc", ".DS_Store", ".print-*", ".book.html")

REPORT_EX = ("examples/read-codebase-zh-rsshub-folo", "rsshub-folo", ["report.json", "report.md"])
DRILLS_EX = ("examples/practice-drills-en-paged-kv", "paged-kv",
             ["drills.json", "README.md", "check.sh", "drill.py", "pytest.ini", "src", "solutions", "tests"])

SKILLS = {
    "read-codebase": ("en", REPORT_EX),
    "read-codebase-zh": ("zh", REPORT_EX),
    "practice-drills": ("en", DRILLS_EX),
    "practice-drills-zh": ("zh", DRILLS_EX),
}


def plan():
    """-> list of (src, dst) pairs, files only."""
    pairs = []
    for skill, (lang, (ex_dir, short, items)) in SKILLS.items():
        sd = ROOT / "skills" / skill
        for f in sorted((ROOT / "toolkit").rglob("*")):
            if f.is_file() and not any(p in f.parts for p in ("__pycache__", ".cache")) and f.suffix != ".pyc" \
                    and f.name != ".DS_Store":
                pairs.append((f, sd / "toolkit" / f.relative_to(ROOT / "toolkit")))
        pairs.append((ROOT / "docs" / f"syntax.{lang}.md", sd / "reference" / "syntax.md"))
        for item in items:
            src = ROOT / ex_dir / item
            files = [src] if src.is_file() else sorted(p for p in src.rglob("*") if p.is_file()
                                                        and "__pycache__" not in p.parts and p.suffix != ".pyc")
            for f in files:
                pairs.append((f, sd / "examples" / short / f.relative_to(ROOT / ex_dir)))
    return pairs


def main(check: bool) -> int:
    pairs = plan()
    stale = [(s, d) for s, d in pairs if not d.exists() or not filecmp.cmp(s, d, shallow=False)]
    # files in the managed folders that no longer have a source
    managed = set(d for _, d in pairs)
    extra = []
    for skill in SKILLS:
        for sub in ("toolkit", "examples"):
            base = ROOT / "skills" / skill / sub
            if base.exists():
                extra += [p for p in base.rglob("*") if p.is_file() and p not in managed
                          and "__pycache__" not in p.parts]
    if check:
        for s, d in stale:
            print("stale ", d.relative_to(ROOT))
        for p in extra:
            print("extra ", p.relative_to(ROOT))
        print(f"{len(pairs)} managed files, {len(stale)} stale, {len(extra)} extra")
        return 1 if stale or extra else 0
    for s, d in stale:
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(s, d)
    for p in extra:
        p.unlink()
    print(f"synced {len(stale)} files, removed {len(extra)} ({len(pairs)} managed)")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
