---
name: read-codebase
description: Explain an open-source codebase as a code-wiki style HTML report plus PDF, written for someone who wants to understand it deeply and then contribute or customize it. Covers the problem, goals and constraints, the architecture, how the components connect, request and data lifecycles and the license, with React-Flow-style diagrams, analogies, and source links pinned to a commit and verified. Use when the user asks to analyze, understand or explain a repo ("what does X do, what problem does it solve, what is hard, how is it solved"), wants a codebase report, guide, wiki or architecture overview, or wants to prepare to contribute to a project. Writes English; use read-codebase-zh for a Chinese report.
---

# Read a codebase → code-wiki report (HTML + PDF)

The deliverable is a single self-contained HTML page in the style of a code wiki: a left table of contents, chapters that go from "why does this exist" down to "which line does it", many small diagrams, a few analogies, and dense links into the source. A PDF printed from the same page goes with it. The reader is a capable engineer who is new to this codebase and wants to **contribute or build on it**. Write for that person.

Everything you need is bundled:

| Path (relative to this skill) | What it is |
|---|---|
| `toolkit/run.sh` | runs any toolkit script with a Python that has `markdown-it-py` (creates a private venv on first use) |
| `toolkit/build_report.py` | `report.json` + Markdown → `report.html` (+ `--pdf`, `--shots`, `--links`, `--strict`) |
| `toolkit/shots.py`, `toolkit/make_pdf.py`, `toolkit/check_links.py` | diagram screenshots, PDF via headless Chrome, external link check |
| `reference/syntax.md` | **read before writing**: containers, flow-diagram DSL, step-through animations, pinned source links |
| `reference/outline.md` | the chapter template and what each chapter must answer |
| `reference/checklist.md` | the quality bar; go through it before you report back |
| `examples/rsshub-folo/` | a complete, verified example (`report.json` + `report.md`, 14 diagrams, 159 pinned links) |

## Workflow

### 1. Scope (don't over-ask)
Default to the whole project, for a contributor audience, in English. Ask only if the target is genuinely ambiguous, for example when several repos share a name. If the user names two related projects (an engine and its client, a library and the service that uses it), cover both and add a chapter on how they connect.

Output goes in its own folder, `~/development/<topic>-report/` by default, **never inside the analyzed repo**. Name the files `report.json`, `report.md`, `report.html` and `report.pdf`.

### 2. Get the source and pin it
- Clone each repo (`git clone --depth 1` is enough for reading) and record `git rev-parse HEAD`. Every source link is pinned to that SHA in `report.json → pins`, with `local` set to the clone so builds read files with `git show` (fast and offline).
- For claims about **history** (when a license changed, when a feature appeared), a shallow clone isn't enough. Use the GitHub API, e.g. `gh api 'repos/O/R/commits?path=LICENSE'`, or fetch the file at an old SHA. Never state history from memory.
- Tell the user the scope and the pinned SHAs in one line, then keep going.

### 3. Research pass: read like a new maintainer
Work through these in order and take notes with exact `path:line`:
1. `README`, `CONTRIBUTING`, `AGENTS.md` / `CLAUDE.md`, `LICENSE` (+ per-package `license` fields, NOTICE, trademark or asset exceptions), docs index.
2. Manifests and build: package.json / pyproject / Cargo.toml / CMake, workspace layout, scripts, how it is built, run, tested and deployed.
3. **Entry points**: the main binary or server startup, CLI entry, exported API.
4. **One real request or data path end to end**: follow a single concrete call (one HTTP request, one `generate()`, one compile) through every layer and write down each hop with its file and line. This becomes the backbone of the report.
5. Core abstractions: the 3–8 types or interfaces everything else is written against.
6. State and storage: caches, databases, queues, sync, lifecycle and cleanup.
7. Configuration and deployment modes; the limits each mode imposes.
8. Extension points: where contributors add things (plugins, routes, ops, backends), and the review rules for them.
9. **What is not in the repo**: closed backends, SaaS dependencies, generated code, binary blobs. Readers who want to customize need this more than anything else.

Verify every non-obvious claim against the code: defaults (read the config code), line numbers, which component calls which. If something is inferred rather than read, say so in the text ("the client only sees the API; the server side is not public").

### 4. Outline
Use `reference/outline.md`. The spine is always:
**overview → requirements/goals/constraints table → architecture map → one chapter per major component → end-to-end lifecycle → (license) → contributing & customizing → source index.**
Each component chapter answers: *what problem does it solve, what constraint makes it hard, how is it solved, how does it connect to its neighbours, where is the code.*

### 5. Write `report.md` + `report.json`
Read `reference/syntax.md` first. Rules that matter most:
- **Diagrams**: aim for one per major idea, 8–16 in a typical report. Use `::: flow` for architecture and data paths, and `::: steps` for lifecycles that unfold over time (each step highlights the nodes involved). Keep node titles short (≤ ~18 Latin / ~11 CJK characters), subtitles ≤ ~24 characters, and edge labels to 1–3 words. Every diagram gets a caption saying what to notice, with a source link.
- **Analogies**: 2–4 per report, each mapping one specific mechanism to something physical, with the mapping made explicit (shelf = block, card = block table). Never decorative, never more than one per section.
- **Source links**: put a `[[alias:path#Lx|label]]` or `[[alias:path@Symbol|label]]` next to every concrete claim; prefer `@Symbol` (it survives your own line-number mistakes). A typical report has 60–150.
- **Tables** for comparisons and the requirements/goals/constraints matrix; prose for reasoning.
- **Code snippets**: short, simplified, and labelled "simplified from <link>". Never paste long files.
- **License chapter** whenever the reader might fork or ship: the license of each part, scenario table (use privately / contribute / publish fork / ship binaries / run as a service), special exceptions (assets, icons, trademarks), CLA, license history. Mark it "not legal advice".

### 6. Build, look, fix (loop until clean)
```bash
bash <skill>/toolkit/run.sh build_report.py <out>/report.json --strict --shots
```
- `--strict` fails on unresolved links, missing files or symbols, line numbers past EOF, overlapping nodes, text wider than its box, edge labels that don't fit their gap, and quality minimums from `report.json → quality`.
- **Open every PNG in `<out>/.shots/` and look at it.** The linter cannot see crossing edges, edges routed through nodes, or a layout that is merely confusing. Fix by moving nodes (fractional `col`/`row` are fine), choosing explicit sides (`a:b -> c:t`), raising `cw`/`rh`, or dropping a label into the caption. Rebuild and look again.
- Then `--links` (every external URL answers 200) and `--pdf`. Check page count and skim two or three PDF pages: `pdftoppm -r 45 -png -f 3 -l 5 report.pdf /tmp/p` if it is available.

### 7. Report back
Reply with the paths to the HTML and PDF, what the report covers (chapters in one line each), the pinned SHAs, and the verification you ran (links checked, diagrams reviewed). Mention any claim you could not verify. If the host can publish pages (an Artifact tool), offer it in one line; don't publish unasked. Commit or push only if the user asks.

## Don'ts
- Don't describe the directory tree file by file. Explain responsibilities and connections, and link the files.
- Don't write a claim you haven't checked in the code at the pinned SHA.
- Don't hand-compute line numbers from a modified working tree. Pins read the pinned commit, so let the builder resolve `@Symbol`.
- Don't let a diagram ship without looking at its screenshot.
- Don't pad with generic text ("this is a powerful framework"). Every paragraph should teach something specific to this codebase.
