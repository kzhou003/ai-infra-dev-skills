#!/usr/bin/env python3
"""Summarize entry points and a lightweight internal import graph.

Usage: python3 -I structure.py <repo path>
Supports JavaScript/TypeScript, Python, Go and Rust. This is heuristic:
dynamic imports, generated modules and language-specific resolution rules
may be missed. Output is capped for agent context.
"""
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

repo = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
SOURCE_EXT = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".py", ".go", ".rs"}
JS_EXT = [".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"]
NOISE = re.compile(
    r"(^|/)(node_modules|vendor|dist|build|\.next|target|third_party|__pycache__|\.venv|venv)/"
    r"|\.min\.js$|\.d\.ts$"
)
ENTRY_NAMES = re.compile(r"(^|/)(main|index|app|server|cli|__main__|manage|background|content|popup|worker)\.[a-z]+$")
TEST = re.compile(r"(^|/)(tests?|__tests__|spec)/|(^|/)test_[^/]*$|[._](test|spec)\.[a-z]+$|_test\.(go|py)$")
JS_IMPORT = re.compile(r"""(?:import\s[^'"]*?from\s*|import\s*\(?\s*|require\s*\(\s*|export\s[^'"]*?from\s*)['"]([^'"]+)['"]""")
PY_FROM = re.compile(r"^\s*from\s+(\.*[\w.]*)\s+import\s+([\w*, ()]+)", re.M)
PY_IMPORT = re.compile(r"^\s*import\s+([\w., ]+)", re.M)
GO_IMPORT_BLOCK = re.compile(r"import\s*\(([^)]*)\)", re.S)
GO_IMPORT_ONE = re.compile(r'import\s+(?:\w+\s+)? "([^"]+)"|import\s+"([^"]+)"')
RS_MOD = re.compile(r"^\s*(?:pub\s+)?mod\s+(\w+)\s*;", re.M)
RS_USE = re.compile(r"^\s*(?:pub\s+)?use\s+(crate|super|self)::(\w+)", re.M)
RS_EXT = re.compile(r"^\s*(?:pub\s+)?use\s+(\w+)::", re.M)

def git_files():
    try:
        out = subprocess.run(["git", "-C", repo, "ls-files"], capture_output=True, text=True, check=True).stdout
        return out.splitlines()
    except (subprocess.CalledProcessError, FileNotFoundError):
        found = []
        for root, dirs, names in os.walk(repo):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            found.extend(os.path.relpath(os.path.join(root, n), repo) for n in names)
        return found

files = [f for f in git_files() if not NOISE.search(f)]
fileset = set(files)
sources = [f for f in files if os.path.splitext(f)[1] in SOURCE_EXT]

def read(path):
    try:
        with open(os.path.join(repo, path), encoding="utf-8", errors="replace") as fh:
            return fh.read(400_000)
    except OSError:
        return ""

go_module = ""
if "go.mod" in fileset:
    m = re.search(r"^module\s+(\S+)", read("go.mod"), re.M)
    go_module = m.group(1) if m else ""

def resolve_js(src, spec):
    if not spec.startswith("."):
        return None
    base = os.path.normpath(os.path.join(os.path.dirname(src), spec))
    for candidate in [base] + [base + e for e in JS_EXT] + [base + "/index" + e for e in JS_EXT]:
        if candidate in fileset:
            return candidate
    return None

def resolve_py(src, module, names):
    if module.startswith("."):
        dots = len(module) - len(module.lstrip("."))
        pkg = os.path.dirname(src)
        for _ in range(dots - 1):
            pkg = os.path.dirname(pkg)
        rest = module.lstrip(".")
        base = os.path.join(pkg, *rest.split(".")) if rest else pkg
    else:
        base = os.path.join(*module.split("."))
    names = [n.strip(" ()").split(" as ")[0].strip() for n in names.split(",")]
    tries = [base + ".py", base + "/__init__.py"]
    tries += [os.path.join(base, n) + ".py" for n in names if n not in ("", "*")]
    tries += ["src/" + t for t in tries]
    hits = [os.path.normpath(t) for t in tries if os.path.normpath(t) in fileset]
    return [h for h in hits if not h.endswith("__init__.py")] or hits

def go_pkg_files(pkg_dir):
    return [f for f in sources if os.path.dirname(f) == pkg_dir and f.endswith(".go") and not f.endswith("_test.go")]

edges = defaultdict(set)
external = Counter()
for src in sources:
    body = read(src)
    ext = os.path.splitext(src)[1]
    if ext in JS_EXT:
        specs = JS_IMPORT.findall(body)
        for spec in specs:
            target = resolve_js(src, spec)
            if target:
                edges[src].add(target)
            elif not spec.startswith("."):
                parts = spec.split("/")
                external["/".join(parts[:2]) if spec.startswith("@") else parts[0]] += 1
    elif ext == ".py":
        for module, names in PY_FROM.findall(body):
            hits = resolve_py(src, module, names)
            edges[src].update(hits)
            if not hits and not module.startswith("."):
                external[module.split(".")[0]] += 1
        for group in PY_IMPORT.findall(body):
            for module in group.split(","):
                module = module.strip().split(" ")[0]
                if module:
                    hits = resolve_py(src, module, "")
                    edges[src].update(hits)
                    if not hits:
                        external[module.split(".")[0]] += 1
    elif ext == ".go":
        specs = GO_IMPORT_ONE.findall(body)
        specs = [next((x for x in pair if x), "") for pair in specs]
        for block in GO_IMPORT_BLOCK.findall(body):
            specs += re.findall(r'"([^"]+)"', block)
        for spec in specs:
            if go_module and spec.startswith(go_module + "/"):
                edges[src].update(go_pkg_files(spec[len(go_module) + 1:]))
            elif go_module and spec == go_module:
                edges[src].update(go_pkg_files(""))
            elif spec:
                external[spec] += 1
    elif ext == ".rs":
        here = os.path.dirname(src)
        for name in RS_MOD.findall(body):
            for candidate in (os.path.join(here, name + ".rs"), os.path.join(here, name, "mod.rs")):
                if os.path.normpath(candidate) in fileset:
                    edges[src].add(os.path.normpath(candidate))
        for _, name in RS_USE.findall(body):
            for candidate in (os.path.join(here, name + ".rs"), os.path.join("src", name + ".rs"), os.path.join("src", name, "mod.rs")):
                if os.path.normpath(candidate) in fileset:
                    edges[src].add(os.path.normpath(candidate))
        for crate in RS_EXT.findall(body):
            if crate not in ("crate", "super", "self", "std", "core", "alloc"):
                external[crate] += 1

for src in list(edges):
    edges[src].discard(src)
    if TEST.search(src):
        del edges[src]
indegree = Counter(target for targets in edges.values() for target in targets)

def line_count(path):
    return read(path).count("\n")

print("## Code size")
print(f"source files: {len(sources)} ({sum(1 for f in sources if TEST.search(f))} tests) | internal import edges: {sum(len(v) for v in edges.values())}")
by_ext = Counter(os.path.splitext(f)[1] for f in sources)
print("by type: " + ", ".join(f"{e} {n}" for e, n in by_ext.most_common(6)))
print("\n## Entry points")
entries = []
if "package.json" in fileset:
    try:
        pkg = json.loads(read("package.json"))
        for key in ("main", "module", "bin"):
            value = pkg.get(key)
            if isinstance(value, str):
                entries.append(f"package.json {key}: {value}")
            elif isinstance(value, dict):
                entries.extend(f"package.json bin {k}: {v}" for k, v in value.items())
        entries.extend(f"package.json script {k}: {v[:100]}" for k, v in list(pkg.get("scripts", {}).items())[:6])
    except (ValueError, TypeError):
        pass
for f in files:
    if f.endswith("manifest.json") and f.count("/") <= 2:
        entries.append(f"extension/app manifest: {f}")
for f in sources:
    if f.count("/") <= 3 and ENTRY_NAMES.search(f) and (indegree[f] == 0 or ENTRY_NAMES.search(f)):
        entries.append(f"{f} ({line_count(f)} lines, imported by {indegree[f]})")
for item in entries[:20]:
    print(item)
if not entries:
    print("No entry point found by name; start from the most imported files.")
print("\n## Most imported internal files (top 15)")
for f, count in indegree.most_common(15):
    print(f"{count:3d}  {f} ({line_count(f)} lines)")
print("\n## Files importing the most internal files (top 10)")
for f, targets in sorted(edges.items(), key=lambda item: -len(item[1]))[:10]:
    if targets:
        print(f"{len(targets):3d}  {f} ({line_count(f)} lines)")
print("\n## Largest source files (top 10)")
for f in sorted(sources, key=line_count, reverse=True)[:10]:
    print(f"{line_count(f):5d}  {f}")
central = {f for f, _ in indegree.most_common(12)} | {f for f, _ in sorted(edges.items(), key=lambda item: -len(item[1]))[:6]}
print("\n## Edges among central files")
shown = 0
for src in sorted(central):
    targets = sorted(t for t in edges.get(src, ()) if t in central)
    if targets and shown < 25:
        print(f"{src} -> {', '.join(targets)}")
        shown += 1
print("\n## Most used external packages (top 15)")
print(", ".join(f"{name} ({count})" for name, count in external.most_common(15)) or "none found")
