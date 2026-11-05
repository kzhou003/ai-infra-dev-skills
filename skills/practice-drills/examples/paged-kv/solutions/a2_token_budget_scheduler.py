"""A2 · One step of a continuous-batching scheduler with chunked prefill — reference solution.

The vLLM v1 scheduler does not have separate "prefill" and "decode" phases. Every request just has
`num_tokens` (prompt + generated so far) and `num_computed_tokens` (how many of those already have
KV in the cache); each step it hands out at most `token_budget` new tokens:

1. RUNNING requests first, in order. Each gets min(remaining, long_prefill_threshold, budget)
   tokens, where remaining = num_tokens - num_computed_tokens (1 for a decoding request).
2. Then WAITING requests, first come first served, while budget is left and fewer than
   max_num_seqs requests are running. A prompt bigger than the budget is split across steps
   (chunked prefill); the request becomes RUNNING as soon as it gets its first chunk.

`update(scheduled)` plays the model: it adds the scheduled tokens to num_computed_tokens, and a
request whose KV caught up with all its tokens samples one new token. A request that reaches
max_new_tokens finishes and leaves the running list.

API
    Request(req_id, num_prompt_tokens, max_new_tokens)               given (dataclass)
    Scheduler(token_budget, max_num_seqs, long_prefill_threshold=0)
        .add(req)                      append to the waiting queue
        .schedule() -> dict[str, int]  req_id -> tokens to run this step (insertion order = batch order)
        .update(scheduled) -> list[str]   apply one model step, return the finished req_ids
        .waiting (deque) / .running (list)
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass
class Request:
    req_id: str
    num_prompt_tokens: int
    max_new_tokens: int
    num_computed_tokens: int = 0    # tokens whose KV is already in the cache
    num_output_tokens: int = 0      # tokens generated so far

    @property
    def num_tokens(self) -> int:
        """All tokens of the sequence so far: prompt + generated."""
        return self.num_prompt_tokens + self.num_output_tokens


class Scheduler:
    def __init__(self, token_budget: int, max_num_seqs: int, long_prefill_threshold: int = 0) -> None:
        self.token_budget = token_budget
        self.max_num_seqs = max_num_seqs
        # 0 = no cap. A cap stops one huge prompt from taking the whole step and stalling every
        # decoding request behind it (vLLM: scheduler_config.long_prefill_token_threshold).
        self.long_prefill_threshold = long_prefill_threshold
        self.waiting: deque[Request] = deque()
        self.running: list[Request] = []

    def add(self, req: Request) -> None:
        self.waiting.append(req)

    def _tokens_for(self, req: Request, budget: int) -> int:
        n = req.num_tokens - req.num_computed_tokens          # 1 while decoding, the rest of the prompt while prefilling
        if 0 < self.long_prefill_threshold < n:
            n = self.long_prefill_threshold
        return min(n, budget)

    def schedule(self) -> dict[str, int]:
        budget = self.token_budget
        out: dict[str, int] = {}

        # 1. RUNNING first: they already hold KV blocks, and starving them wastes that memory and
        #    hurts inter-token latency. Order matters only when the budget runs out mid-list.
        for req in self.running:
            if budget == 0:
                break
            n = self._tokens_for(req, budget)
            if n > 0:
                out[req.req_id] = n
                budget -= n

        # 2. WAITING, FCFS. Stop (don't skip) when a request cannot be admitted: skipping would let
        #    later small requests overtake an earlier big one forever (starvation).
        while self.waiting and budget > 0 and len(self.running) < self.max_num_seqs:
            req = self.waiting.popleft()
            n = self._tokens_for(req, budget)
            self.running.append(req)        # RUNNING from its first chunk on
            out[req.req_id] = n
            budget -= n

        assert budget >= 0 and len(self.running) <= self.max_num_seqs
        return out

    def update(self, scheduled: dict[str, int]) -> list[str]:
        finished: list[str] = []
        for req in list(self.running):
            n = scheduled.get(req.req_id, 0)
            if n == 0:
                continue
            req.num_computed_tokens += n
            # A forward pass only yields a usable next token when it covered the LAST known token:
            # a partial prefill chunk produces logits nobody samples from.
            if req.num_computed_tokens == req.num_tokens:
                req.num_output_tokens += 1
                if req.num_output_tokens >= req.max_new_tokens:
                    self.running.remove(req)
                    finished.append(req.req_id)
        return finished
