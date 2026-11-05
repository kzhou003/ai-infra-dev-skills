---
name: practice-drills
description: Build a hands-on drills repository for mastering a technical domain (AI infra, LLM serving, GPU kernels, compilers, distributed systems, any codebase). It contains HTML knowledge pages explaining the domain; core exercises, each with a skeleton and acceptance tests; heavily commented reference solutions; one explainer and hint page per exercise with React-Flow-style diagrams, analogies, step-through animations, worked I/O examples and three spoiler levels; and a PDF book. Everything runs on CPU with ./check.sh. Use when the user asks for drills, exercises, practice problems, coding katas, interview prep, a self-study course or training camp on a topic or project, or "something like nano-vllm-omni-drills / gpu-kernel-drills". Writes English; use practice-drills-zh for Chinese.
---

# Practice drills: knowledge pages + core exercises + tests + commented solutions + hint pages

The deliverable is a git repository that someone can clone and learn from in one-hour sessions:

```
<name>-drills/
  README.md                  what this is, quick start, progress table (☐ per drill)
  drills.json                single source of truth: title, lang, pins, tracks, drills, knowledge pages
  check.sh  drill.py  pytest.ini  .gitignore
  mine/<stem>.py             skeletons, every function raises NotImplementedError   ← the learner writes here
  tests/test_<stem>.py       acceptance tests (CPU, deterministic, < 1 s each)
  solutions/<stem>.py        reference solutions with explanatory comments
  src/index.md               hub intro: how to use, setup, suggested order
  src/knowledge/<name>.md    domain knowledge pages
  src/hints/<stem>.md        one explainer + hints page per drill
  index.html  knowledge/*.html  hints/*.html  <name>.pdf      ← built, committed
```

Bundled with this skill:

| Path | What it is |
|---|---|
| `toolkit/run.sh` | runs toolkit scripts with a Python that has `markdown-it-py` |
| `toolkit/build_drills.py` | builds hub + knowledge + hint pages (+ `--pdf --shots --links --strict`) |
| `toolkit/gen_stubs.py` | `solutions/` → `mine/` skeletons (keeps signatures, docstrings, `given` helpers) |
| `toolkit/templates/drills/` | `check.sh`, `drill.py`, `pytest.ini`, `gitignore` to copy into a new repo |
| `reference/syntax.md` | **read before writing pages**: containers, flow DSL, steps, cells, code embeds, pinned links |
| `reference/structure.md` | drills.json schema, the hint-page and knowledge-page templates, the README template |
| `reference/checklist.md` | the quality bar; go through it before reporting back |
| `examples/paged-kv/` | a complete small example: 2 drills mirroring vLLM v1's block pool and scheduler |

## Workflow

### 1. Scope (decide sensible defaults; ask only what you can't infer)
- **Domain and anchor projects**: the drills mirror real code. Pick 1–3 reference repos (e.g. vLLM, SGLang, FlashInfer, Triton) and the subsystems that matter.
- **Size**: 8–16 drills of 30–75 minutes for a first version (the user can ask for more), grouped into 2–5 tracks, ordered from foundations to integration. A drill may depend on an earlier one; say so.
- **Language**: English prose (this skill). Code, identifiers and test names are always English.
- Location: `~/development/<name>-drills/` unless told otherwise. If the user gave a GitHub URL, that is the remote.

Post the curriculum (a table: id, title, minutes, which real function it mirrors) in one message and continue. Don't wait for approval unless the user asked to review it first.

### 2. Research and pin
Clone the anchor repos, record SHAs into `drills.json → pins` (with `local` paths), and read the real implementations of each mechanism. Note the exact functions and lines each drill mirrors; they become the "Follow-ups and the real source" links. Verify claims (defaults, ordering, edge-case behaviour) in the code.

### 3. Design each drill (one mechanism, one hour)
- **One core mechanism** that a practitioner must really understand (a scheduler step, a block allocator, an attention mask, a layout function, a retry protocol...). Not a toy and not a whole system.
- **Pure Python** (+ numpy; torch CPU only if essential), deterministic, no network or GPU. Model hardware or distributed effects with simple simulations (fake clocks, simulated workers, counted bytes).
- **API spec lives in the solution's module docstring and function docstrings**, because those are copied into the skeleton. Every behaviour a test checks must be stated there. No hidden requirements.
- **`given`** (in drills.json): helpers, data classes and constants the learner should not have to write, so the hour goes to the mechanism itself.
- Name the drill after what it builds; give minutes and difficulty honestly.

### 4. For each drill, in this order
1. **Solution first** (`solutions/<stem>.py`). Comments explain *why*: the invariant being kept, why this order of operations, what breaks if you do it the obvious way, complexity, how the real project differs. Comments inside function bodies are removed from the skeleton, so put explanations there freely.
2. **Tests** (`tests/test_<stem>.py`): load via `from drill import load; m = load("<stem>")`. Test behaviour, edge cases and invariants: each pitfall you will list on the hint page should have a test that catches it. Use descriptive names (`test_failed_allocation_changes_nothing`). Long randomized or simulated runs check invariants (budget never exceeded, no leaks).
3. `bash <skill>/toolkit/run.sh gen_stubs.py drills.json` → `mine/<stem>.py`.
4. **Verify both directions**: `DRILL_IMPL=solutions ./check.sh <id>` must pass, and `./check.sh <id>` must fail with NotImplementedError. If a test passes on the stub, it tests nothing.
5. **Hint page** (`src/hints/<stem>.md`) following `reference/structure.md`: the drill in one minute → intuition and analogy → diagram → step-through animation → pitfalls → L1 / L2 / L3 hints → reference solution (embedded) → follow-ups and real source. **Every number in an example or a step is produced by running the solution** (a short script), never computed by hand.

### 5. Knowledge pages (`src/knowledge/*.md`)
One to four pages that make the drills meaningful: the problem the domain solves, why the naive approach fails, the key mechanisms with diagrams and links into the real code, one or two analogies, and a closing table *drill → what it rebuilds → source*. Write them after the drills, so they explain exactly what the drills need.

### 6. README, build, look, fix
- README from the template in `reference/structure.md`: one-paragraph intro, quick start, layout, how to do a drill, a progress table with ☐, and links to the hub page and PDF.
- `bash <skill>/toolkit/run.sh build_drills.py drills.json --strict --shots`. Fix every error, then **open every PNG under `.shots/` and look**: no edge through a node, no label on a node, no needless crossings. Rebuild until clean.
- `--links` (external URLs answer 200), then `--pdf`. Spot-check a few PDF pages.
- Final run: `DRILL_IMPL=solutions ./check.sh all` passes; `./check.sh all` fails on every drill; `gen_stubs.py --check` passes.

### 7. Git and publishing (only when asked)
Commit and push only if the user asked. When they did: `git init -b main`, commit with a descriptive message, add the remote and push. Optionally enable GitHub Pages from `main` / root so `index.html` is browsable (`gh api -X POST repos/O/R/pages -f 'source[branch]=main' -f 'source[path]=/'`), then verify the live URL.

### 8. Report back
Paths, the drill table, the test results in both directions, the diagram review, the PDF page count, and the remote/Pages URL if pushed.

## Don'ts
- Don't write tests that check implementation details (private names, exact data structures). Test observable behaviour.
- Don't let a docstring and a test disagree; the docstring is the spec.
- Don't hand-compute walk-through numbers; run the solution.
- Don't put the answer in the skeleton: function bodies are stubbed, so explanations belong in body comments.
- Don't make drills that need a GPU, network or large downloads.
- Don't ship a diagram you haven't looked at.
