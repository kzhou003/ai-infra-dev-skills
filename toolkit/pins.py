"""Pinned source links: every link to upstream code points at a fixed commit, and is verified.

A project declares its pinned repositories in its config file (report.json / drills.json):

    "pins": {
      "vllm":  {"repo": "vllm-project/vllm", "sha": "4f2d...", "local": "~/development/vllm"},
      "torch": {"repo": "pytorch/pytorch",   "sha": "fbab7cc..."}
    }

`local` is optional. When it points at a clone that contains `sha`, files are read with
`git show <sha>:<path>` (fast, offline). Otherwise the file tree comes from the GitHub API and file
contents from raw.githubusercontent.com, cached under `.cache/sources/` next to the config file.
Set GITHUB_TOKEN to raise the API rate limit.

Link macro (in Markdown, outside code):

    [[vllm:vllm/core/scheduler.py]]                      file, label = path
    [[vllm:vllm/core/scheduler.py#L120]]                 one line
    [[vllm:vllm/core/scheduler.py#L120-L180|label]]      range + custom label
    [[vllm:vllm/core/scheduler.py@Scheduler]]            line where `Scheduler` is defined
    [[vllm:vllm/core/scheduler.py@Scheduler.schedule]]   method inside a class (searched after the class)
    [[vllm:vllm/core/]]                                  directory (tree link)
    [[vllm]]                                             repository root at the pinned commit
    [[here:solutions/p01.py|label]]                      file in THIS project (relative link)

Every macro is resolved at build time: a missing path, a line past the end of the file, or a
symbol that cannot be found is a build error, so published pages never contain dead links.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

MACRO = re.compile(
    r"\[\[([A-Za-z0-9_-]+)(?::([^\]|#@]*))?(?:#L(\d+)(?:-L(\d+))?)?(?:@([^\]|]+))?(?:\|([^\]]+))?\]\]"
)

DEF_KW = (r"(?:export\s+)?(?:default\s+)?(?:pub(?:\([a-z]+\))?\s+)?(?:async\s+)?(?:static\s+)?"
          r"(?:def|class|function|fn|struct|enum|trait|impl|interface|type|const|let|var|module|"
          r"__global__\s+void|void|template|namespace)\b")


class PinError(Exception):
    pass


class Pins:
    def __init__(self, pins: dict, root: Path):
        self.pins = pins or {}
        self.root = Path(root)
        self.cache = self.root / ".cache" / "sources"
        self._trees: dict[str, tuple[set, set]] = {}
        self._files: dict[tuple[str, str], list[str]] = {}
        self.errors: list[str] = []
        self.count = 0

    # ---------- repository access ----------
    def _local(self, alias):
        p = self.pins[alias].get("local")
        if not p:
            return None
        p = Path(os.path.expanduser(p))
        if not (p / ".git").exists():
            return None
        sha = self.pins[alias]["sha"]
        ok = subprocess.run(["git", "-C", str(p), "cat-file", "-e", f"{sha}^{{commit}}"],
                            capture_output=True).returncode == 0
        return p if ok else None

    def _http(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "ai-infra-dev-skills"})
        tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        if tok and "api.github.com" in url:
            req.add_header("Authorization", f"Bearer {tok}")
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read()

    def tree(self, alias):
        """-> (files, dirs) at the pinned sha."""
        if alias in self._trees:
            return self._trees[alias]
        repo, sha = self.pins[alias]["repo"], self.pins[alias]["sha"]
        local = self._local(alias)
        if local:
            out = subprocess.run(["git", "-C", str(local), "ls-tree", "-r", "--name-only", sha],
                                 capture_output=True, text=True, check=True).stdout
            files = set(out.split("\n")) - {""}
        else:
            cf = self.cache / f"{alias}-{sha[:12]}.tree.json"
            if not cf.exists():
                cf.parent.mkdir(parents=True, exist_ok=True)
                data = self._http(f"https://api.github.com/repos/{repo}/git/trees/{sha}?recursive=1")
                cf.write_bytes(data)
            data = json.loads(cf.read_text())
            if data.get("truncated"):
                raise PinError(f"{alias}: GitHub tree listing is truncated; set `local` to a clone")
            files = {e["path"] for e in data["tree"] if e["type"] == "blob"}
        dirs = set()
        for f in files:
            parts = f.split("/")[:-1]
            for i in range(1, len(parts) + 1):
                dirs.add("/".join(parts[:i]))
        self._trees[alias] = (files, dirs)
        return files, dirs

    def read(self, alias, path) -> list[str]:
        key = (alias, path)
        if key in self._files:
            return self._files[key]
        repo, sha = self.pins[alias]["repo"], self.pins[alias]["sha"]
        local = self._local(alias)
        if local:
            text = subprocess.run(["git", "-C", str(local), "show", f"{sha}:{path}"],
                                  capture_output=True, check=True).stdout.decode("utf-8", "replace")
        else:
            cf = self.cache / alias / sha[:12] / path
            if not cf.exists():
                cf.parent.mkdir(parents=True, exist_ok=True)
                cf.write_bytes(self._http(f"https://raw.githubusercontent.com/{repo}/{sha}/{path}"))
            text = cf.read_text(encoding="utf-8", errors="replace")
        lines = text.split("\n")
        self._files[key] = lines
        return lines

    # ---------- symbol lookup ----------
    def find_symbol(self, alias, path, symbol) -> int:
        lines = self.read(alias, path)
        start = 0
        parts = symbol.split(".")
        for k, name in enumerate(parts):
            n = re.escape(name)
            pats = [re.compile(rf"^\s*{DEF_KW}[^\n]*?\b{n}\b"),               # def / class / fn name
                    re.compile(rf"^\s*(?:[\w.]+\s+)*{n}\s*(?:=|:|\()"),          # name = / name: / name(
                    re.compile(rf"\b{n}\b")]                                   # anywhere (last resort)
            hit = None
            for pat in pats:
                for i in range(start, len(lines)):
                    if pat.search(lines[i]):
                        hit = i
                        break
                if hit is not None:
                    break
            if hit is None:
                raise PinError(f"{alias}:{path}@{symbol}: `{name}` not found")
            start = hit + (1 if k < len(parts) - 1 else 0)
            last = hit
        return last + 1

    # ---------- macro rendering ----------
    def url(self, alias, path="", l0=None, l1=None, is_dir=False):
        repo, sha = self.pins[alias]["repo"], self.pins[alias]["sha"]
        if not path:
            return f"https://github.com/{repo}/tree/{sha}"
        url = f"https://github.com/{repo}/{'tree' if is_dir else 'blob'}/{sha}/{path}"
        if l0:
            url += f"#L{l0}" + (f"-L{l1}" if l1 and l1 != l0 else "")
        return url

    def resolve(self, m: re.Match, here_prefix: str = "", here_root: Path | None = None) -> tuple[str, str]:
        """-> (href, label) for one macro match; records errors instead of raising."""
        alias, path, l0, l1, sym, label = m.groups()
        path = (path or "").strip()
        self.count += 1
        if alias == "here":
            p = (here_root or self.root) / path
            if not p.exists():
                self.errors.append(f"[[here:{path}]]: no such file in this project")
            return here_prefix + path, label or path
        if alias not in self.pins:
            self.errors.append(f"[[{alias}:...]]: alias not declared in pins")
            return "#", label or path or alias
        if not path:
            return self.url(alias), label or self.pins[alias]["repo"]
        try:
            files, dirs = self.tree(alias)
            clean = path.rstrip("/")
            is_dir = clean in dirs
            if not is_dir and clean not in files:
                raise PinError(f"{alias}:{path}: not in {self.pins[alias]['repo']}@{self.pins[alias]['sha'][:8]}")
            if is_dir and (l0 or sym):
                raise PinError(f"{alias}:{path}: line/symbol on a directory")
            if sym:
                l0 = self.find_symbol(alias, clean, sym)
                l1 = None
            elif l0:
                n = len(self.read(alias, clean))
                for ln in (l0, l1):
                    if ln and int(ln) > n:
                        raise PinError(f"{alias}:{path}#L{ln}: file has only {n} lines")
            shown = label or (clean + ("/" if is_dir else "") + (f"@{sym}" if sym else (f":{l0}" if l0 else "")))
            return self.url(alias, clean, l0, l1, is_dir), shown
        except PinError as e:
            self.errors.append(str(e))
            return "#", label or path
        except Exception as e:  # network etc.
            self.errors.append(f"{alias}:{path}: {type(e).__name__}: {e}")
            return "#", label or path
