"""Generate mine/<stem>.py skeletons from solutions/<stem>.py.

    python3 gen_stubs.py path/to/drills.json            # writes the mine/ files that do not exist yet
    python3 gen_stubs.py path/to/drills.json --force    # overwrite (destroys the learner's work!)
    python3 gen_stubs.py path/to/drills.json --check    # verify every stub raises NotImplementedError

Each public function / method keeps its signature and docstring; its body becomes
`raise NotImplementedError("<name>")`. Names listed in the drill's "given" (e.g. "Block",
"Pool.__init__", "CONSTANT") are copied verbatim: data classes, helpers and fixtures the learner
should not have to write. Private helpers (leading underscore) that are not given are removed, so
the learner can structure their own code. Comments inside removed bodies disappear with them,
which is what keeps the solution's explanations out of the skeleton.
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


def stub(src: str, given: set[str], drill_id: str) -> str:
    lines = src.splitlines(keepends=True)
    tree = ast.parse(src)
    edits = []   # (start0, end0_exclusive, replacement lines)

    def visit(body, prefix=""):
        for node in body:
            if isinstance(node, ast.ClassDef):
                if node.name in given:
                    continue
                visit(node.body, prefix + node.name + ".")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                full = prefix + node.name
                if full in given:
                    continue
                start = (node.decorator_list[0].lineno if node.decorator_list else node.lineno) - 1
                if node.name.startswith("_") and not node.name.startswith("__"):
                    edits.append((start, node.end_lineno, []))
                    continue
                first = node.body[0]
                has_doc = (isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant)
                           and isinstance(first.value.value, str))
                indent = " " * first.col_offset
                body_start = first.end_lineno if has_doc else first.lineno - 1
                # keep comment lines that sit between the signature and the first statement out of it
                edits.append((body_start, node.end_lineno, [f'{indent}raise NotImplementedError("{full}")\n']))

    visit(tree.body)
    for s, e, rep in sorted(edits, reverse=True):
        lines[s:e] = rep
    out = "".join(lines)
    out = re.sub(r"(?i)reference solution", f"your implementation (run ./check.sh {drill_id.lower()})", out, count=1)
    ast.parse(out)
    return out


def main(cfg_path: Path, force=False, check=False) -> int:
    cfg_path = Path(cfg_path).resolve()
    root = cfg_path.parent
    cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
    bad = 0
    for d in cfg["drills"]:
        sol = root / "solutions" / f"{d['stem']}.py"
        mine = root / "mine" / f"{d['stem']}.py"
        if not sol.exists():
            print(f"missing {sol.relative_to(root)}")
            bad += 1
            continue
        text = stub(sol.read_text(encoding="utf-8"), set(d.get("given", [])), d["id"])
        if check:
            ok = mine.exists() and "NotImplementedError" in mine.read_text(encoding="utf-8")
            if not ok:
                print(f"{mine.relative_to(root)}: missing or has no NotImplementedError")
                bad += 1
            continue
        if mine.exists() and not force:
            print("skip  ", mine.relative_to(root))
            continue
        mine.parent.mkdir(exist_ok=True)
        mine.write_text(text, encoding="utf-8")
        print("wrote ", mine.relative_to(root))
    init = root / "mine" / "__init__.py"
    if not check and not init.exists():
        init.write_text("", encoding="utf-8")
    return 1 if bad else 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        raise SystemExit(__doc__)
    sys.exit(main(Path(args[0]), force="--force" in sys.argv, check="--check" in sys.argv))
