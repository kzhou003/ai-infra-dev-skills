# Structure and page templates: practice-drills

## drills.json

```json
{
  "title": "LLM serving drills",
  "brand": "Serving drills",                         // short name in the left nav (optional)
  "kicker": "Self-study drills",                     // small caps line on the hub page (optional)
  "lede": "One paragraph: what you will be able to build and explain afterwards.",
  "lang": "en",
  "slug": "serving-drills",                          // localStorage key for progress ticks
  "repo_url": "https://github.com/me/serving-drills", // optional: file links go to GitHub
  "pins": {
    "vllm": {"repo": "vllm-project/vllm", "sha": "<40-hex>", "local": "~/development/vllm"}
  },
  "tracks": [{"id": "A", "title": "Track A · Memory", "desc": "One line on what this track covers."}],
  "drills": [
    {"id": "A1", "stem": "a1_block_pool", "title": "BlockPool: ref counts, LRU free queue, prefix cache",
     "minutes": 50, "difficulty": "medium", "track": "A",
     "given": ["NoFreeBlocks", "hash_blocks", "BlockPool.ref_count"]}
  ],
  "knowledge": ["overview"],
  "pdf": "serving-drills.pdf",
  "quality": {"flows": 1, "steps": 1, "analogies": 1, "hints": 3}
}
```

- `stem` = file stem used in `mine/`, `tests/test_<stem>.py`, `solutions/`, `src/hints/`. Start it with the lower-case id (`a1_...`) so `./check.sh a1` finds it.
- `given` = names copied verbatim into the skeleton (`Class`, `Class.method`, `function`, `CONSTANT`).
- `quality` = minimum per hint page; `--strict` makes misses errors.

## Solution file template

```python
"""A1 · <Title> — reference solution.

<Two to five lines: what this is in the real system, which function it mirrors.>

- <Rule 1 the tests check>
- <Rule 2 ...>

API
    name(args) -> result        <one line each; mark given items "given">
"""
from __future__ import annotations


def given_helper(...):
    """Docstring kept in the skeleton."""
    ...


class Thing:
    def method(self, x: int) -> int:
        """What it returns, when it raises. Kept in the skeleton."""
        # WHY comments go here: the invariant, why this order, what the obvious approach breaks,
        # how the real project does it (and why it differs). Removed from the skeleton.
        ...
```

## Test file template

```python
import pytest

from drill import load

m = load("a1_block_pool")


def test_<observable_behaviour>():
    ...


def test_<pitfall_from_the_hint_page>_is_handled():
    ...


def test_<invariant>_over_a_long_random_run():
    ...
```

## Hint page template (`src/hints/<stem>.md`)

```markdown
lede: One sentence: what this drill builds and why it matters.
# A1 · <Title>

## The drill in one minute
- **Where it lives**: <when the real system calls this> ([[alias:path@Symbol|Symbol]]).
- **You implement**: <functions>. <given items> are given.
- **The rules that make it subtle**: numbered, 3–5 items.

**The tests check**: <one line per test, joined with ·>

## Intuition
::: callout analogy <Concrete physical analogy>
<Map every moving part explicitly.>
:::

## <The data structures / The algorithm>
::: flow <title>
...
cap: <the invariant or the thing to notice>
:::

## Step through one scenario
::: steps <scenario name with concrete sizes>
::: flow
... (small diagram whose nodes the steps highlight)
:::
--- step Start {hl=...}
<state, with {{cells: ...}} where it helps>
--- step <operation> {hl=...}
<what happens and why; numbers produced by running the solution>
:::

## Pitfalls
- **<mistake>.** <what goes wrong, which test catches it>

## Hints
::: hint 1 I/O examples and the key questions
<python block with concrete calls and results (run them!)>
#### Key questions
1. ...
:::

::: hint 2 Approach and common traps
<state to keep; algorithm in 4–8 steps; traps>
:::

::: hint 3 Detailed answers
::: answer Answers to the key questions
1. ...
:::
:::

## Reference solution
::: solution solutions/<stem>.py
{{code: solutions/<stem>.py}}
:::

## Follow-ups and the real source
- <An interview-style follow-up question that extends the drill>
- <How the real system handles what the drill simplified, with links>
```

## Knowledge page template (`src/knowledge/<name>.md`)

```markdown
lede: What this page explains in one sentence.
# <Topic>

## The problem
<what goes wrong without this; a table of facts → consequences>

### The fix: <mechanism>
<prose + ::: flow + one analogy>

## <Mechanism 2>
...

## Where the drills fit
| Drill | Rebuilds | Source |
|---|---|---|
| A1 ... | ... | [[alias:path@Symbol|file]] |
```

## Hub intro (`src/index.md`)

Setup commands (`python3 -m venv .venv && .venv/bin/pip install pytest numpy`), the `./check.sh` usage, how to do one drill (read 5 min → implement → tests → compare), the suggested order and dependencies. No `lede:` line needed.

## README template

```markdown
# <name>-drills

<One paragraph: N drills of ~1 hour that each rebuild one core mechanism of <domain>,
mirroring <projects> at pinned commits. CPU only.>

- Browse: open `index.html` (or the GitHub Pages URL) · PDF: `<name>.pdf`
- `mine/` skeletons · `tests/` acceptance tests · `solutions/` commented reference solutions
- Explainer + hints per drill: `hints/<stem>.html`; domain background: `knowledge/`

## Quick start
    python3 -m venv .venv && .venv/bin/pip install pytest
    ./check.sh a1                # your mine/a1_*.py
    ./check.sh a1 --solutions    # the reference solution
    ./check.sh all

## How to do a drill
1. Read the explainer page (5–10 min). 2. Implement in `mine/` within the time on the card.
3. Run the tests; open hints only after 10–15 minutes stuck. 4. Compare with the solution and follow-ups.

## Progress
| ✓ | ID | Drill | Minutes | Difficulty |
|---|----|-------|---------|------------|
| ☐ | A1 | ... | 50 | medium |

## Rebuilding the pages
    bash <toolkit>/run.sh build_drills.py drills.json --strict --pdf

## License
<MIT for original material; note that linked upstream code keeps its own license.>
```
