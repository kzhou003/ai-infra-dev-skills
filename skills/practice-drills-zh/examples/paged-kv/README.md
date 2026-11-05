# paged-kv drills (example project)

Two one-hour drills that rebuild the heart of vLLM v1's memory management and scheduling in plain Python: a ref-counted **block pool with prefix caching** and **one step of a continuous-batching scheduler** with chunked prefill. They mirror `vllm/v1/core/block_pool.py` and `vllm/v1/core/sched/scheduler.py` at commit `5e65d6b`. CPU only.

This is the reference example for the `practice-drills` skill: a real drills repository is the same shape with 8–16 drills.

- Browse: open `index.html` · PDF: `paged-kv-drills.pdf`
- `mine/` skeletons · `tests/` acceptance tests · `solutions/` commented reference solutions
- Explainer + hints per drill: `hints/<stem>.html`; domain background: `knowledge/overview.html`

## Quick start

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
./check.sh a1                # test your mine/a1_block_pool.py
./check.sh a1 --solutions    # test the reference solution
./check.sh all
```

## How to do a drill

1. Read the explainer page (5–10 min).
2. Implement in `mine/` within the time on the card.
3. Run the tests; open the hints only after 10–15 minutes stuck (L1 → L2 → L3).
4. Compare with the commented solution and the follow-up questions.

## Progress

| ✓ | ID | Drill | Minutes | Difficulty |
|---|----|-------|---------|------------|
| ☐ | A1 | BlockPool: ref counts, LRU free queue, prefix cache | 50 | medium |
| ☐ | A2 | Scheduler step: token budget, chunked prefill, FCFS admission | 45 | medium |

## Rebuilding the pages

```bash
bash ../../toolkit/run.sh build_drills.py drills.json --strict --pdf
bash ../../toolkit/run.sh gen_stubs.py drills.json        # regenerate missing mine/ stubs
```
