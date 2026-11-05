lede: One scheduling step of a continuous-batching engine: hand out a fixed token budget, running requests first, then new prompts in arrival order, splitting long prompts into chunks.
# A2 · Scheduler step: token budget, chunked prefill, FCFS admission

## The drill in one minute

- **Where it lives**: the engine calls `schedule()` once per forward pass; the result is the batch. In vLLM v1 this is [[vllm:vllm/v1/core/sched/scheduler.py@Scheduler.schedule|Scheduler.schedule]].
- **You implement**: `Scheduler.__init__`, `add`, `schedule() -> {req_id: num_tokens}` and `update(scheduled) -> finished ids`. `Request` is given.
- **One formula drives everything**: a request needs `num_tokens − num_computed_tokens` more tokens, where `num_tokens = prompt + generated`. That is the rest of the prompt while prefilling and exactly 1 while decoding.
- **Rules**: running first, in order · then waiting FCFS while budget > 0 and `len(running) < max_num_seqs` · each request gets `min(need, threshold, budget)` · a request becomes running with its first chunk · never skip the head of the waiting queue.
- **update**: add the scheduled tokens to `num_computed_tokens`; if that caught up with `num_tokens`, one token is generated; at `max_new_tokens` the request finishes and leaves `running`.

## Intuition

::: callout analogy Burner slots in a kitchen
Every minute the kitchen has 8 burner-slots. Dishes already on the stove each need one slot to cook their next bite, so they are served first. New orders get what is left, in the order they came in. A banquet order that needs 30 slots is cooked over several minutes instead of blocking the kitchen. And the kitchen never lets a small order jump ahead of a waiting banquet, or the banquet would wait forever.
:::

::: flow How the budget is spent in one step
cfg cw=190 rh=90 nw=164
n b 0 0.5 "budget = 8" "token_budget" k=dark
n r1 1 0 "running: a" "decode → 1" k=pass
n r2 1 1 "running: c" "prefill rest → 3" k=pass
n w1 2 0 "waiting: b" "30-token prompt" k=warn
n chunk 3 0 "b gets 4" "chunk; now running" k=warn
n w2 2 1 "waiting: d" "not reached" k=ghost
e b -> r1
e b -> r2
e r1 -> w1
e r2 -> w1
e w1 -> chunk
e w1 -> w2 "budget 0" dash
cap: Running first: `a` 1 + `c` 3 = 4, leaving 4 for `b`, the head of the waiting queue. 1 + 3 + 4 = 8, so the budget is gone and `d` waits for the next step. Even if budget were left, `d` could never be admitted ahead of `b`: FCFS.
:::

## Step through a small run

::: steps budget 8, max_num_seqs 2, two requests
--- step Step 1: a arrives (prompt 5, wants 3 tokens)
`a` needs 5 − 0 = 5 → gets 5. `schedule() == {"a": 5}`. After `update`, computed = 5 = num_tokens → `a` produces **token 1** (num_tokens becomes 6).
--- step Step 2: b arrives (prompt 20, wants 1 token)
Running first: `a` needs 6 − 5 = 1 → 1 → **token 2**. Budget left 7 → `b` gets min(20, 7) = 7 and becomes running. `{"a": 1, "b": 7}`. `b` produces nothing yet: 7 < 20.
--- step Step 3: a finishes
`a` → 1 → **token 3** = max_new_tokens → **finished**, leaves running. `b` needs 20 − 7 = 13 → gets the remaining 7 (computed 14). `update` returns `["a"]`.
--- step Step 4: b finishes
Only `b` is running: needs 6 → gets 6 → computed 20 = num_tokens → first token → finished (max_new_tokens = 1). `update` returns `["b"]`; step 5 schedules nothing.
:::

## Pitfalls

- **Treating decode and prefill as different code paths.** One formula covers both; separate paths usually double-count or forget the token produced by the last prefill chunk.
- **Generating a token after a partial chunk.** Only a pass that reaches `num_tokens` produces a token.
- **Skipping a blocked waiting request** to admit a smaller one: passes a quick test, fails the FCFS test, and starves big prompts in production.
- **Checking `max_num_seqs` against waiting instead of running**, or after appending.
- **Iterating over `running` while removing from it** in `update`: iterate over a copy.
- **Forgetting the threshold** applies to running prefills too, not only new ones.

## Hints

::: hint 1 I/O examples and the key questions
```python
s = Scheduler(token_budget=8, max_num_seqs=4)
s.add(Request("a", num_prompt_tokens=20, max_new_tokens=2))
s.schedule()          # {"a": 8}
s.update({"a": 8})    # []        no token yet: 8 < 20
s.schedule()          # {"a": 8}
s.update({"a": 8}); s.schedule()   # {"a": 4}
```

#### Key questions

1. What is `need` for a request that is decoding? For one halfway through its prompt?
2. Why serve running requests before waiting ones?
3. When the head of the waiting queue gets 0 tokens, do you try the next one?
4. In `update`, how do you know whether this step produced a token for a request?
:::

::: hint 2 Approach and common traps
- `need = req.num_tokens - req.num_computed_tokens`; cap with the threshold if `0 < threshold < need`; then `min(need, budget)`.
- `schedule`: loop over `running` while budget > 0; then `while waiting and budget > 0 and len(running) < max_num_seqs`: popleft, compute n, append to running, record.
- `update`: for each running request with `n > 0`: `num_computed_tokens += n`; if it equals `num_tokens`, `num_output_tokens += 1`; at `max_new_tokens` remove and report. Iterate over `list(self.running)`.
:::

::: hint 3 Detailed answers
::: answer Answers to the key questions
1. Decoding: exactly 1 (the token generated in the previous step has no KV yet). Halfway: the rest of the prompt, possibly capped by the threshold and the budget.
2. They already hold KV blocks and their users are waiting for the next token; starving them wastes memory and makes inter-token latency spiky.
3. No. With `budget > 0` the head always gets at least 1 token, so the loop only stops on budget 0 or `max_num_seqs`. Stopping instead of skipping is what makes the queue FCFS.
4. Compare after adding: `num_computed_tokens == num_tokens` means the pass covered the last known token, so its logits are sampled.
:::
:::

## Reference solution

::: solution solutions/a2_token_budget_scheduler.py
{{code: solutions/a2_token_budget_scheduler.py}}
:::

## Follow-ups and the real source

- Real schedulers must also get KV blocks for every scheduled token (drill A1). What should happen when a running request cannot get a block? Read how vLLM preempts the lowest-priority running request in [[vllm:vllm/v1/core/sched/scheduler.py@Scheduler.schedule|schedule]].
- With prefix caching, a new request may start with `num_computed_tokens > 0`. Which line of your code changes?
- The real loops: running first at [[vllm:vllm/v1/core/sched/scheduler.py#L209-L221|L209–L221]], waiting at [[vllm:vllm/v1/core/sched/scheduler.py#L348-L351|L348–L351]], the long-prefill cap at [[vllm:vllm/v1/core/sched/scheduler.py#L219|L219]].
