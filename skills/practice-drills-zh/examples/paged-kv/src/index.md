## How to use this project

Each drill implements one core mechanism of an LLM serving engine in plain Python. Everything runs on CPU in well under a second.

```bash
python3 -m venv .venv && .venv/bin/pip install pytest
./check.sh a1                 # test your mine/a1_block_pool.py
./check.sh a1 --solutions     # test the reference solution
./check.sh all                # every drill
```

1. **Read the knowledge page first** (10 minutes). It explains why paged KV cache and continuous batching exist, with diagrams linked to the vLLM source.
2. **Read the drill's explainer page**: the problem, an analogy, a diagram and a step-through animation.
3. **Implement it** in `mine/` within the time on the card. Only open the hints when you have been stuck for 10–15 minutes: L1 points the direction, L2 breaks the problem down, L3 is almost the answer.
4. **Run the tests**, fix, then compare with the commented reference solution and the follow-up questions.
