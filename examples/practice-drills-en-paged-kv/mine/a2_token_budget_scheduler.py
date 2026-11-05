"""A2 · One step of a continuous-batching scheduler with chunked prefill — your implementation (run ./check.sh a2).

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
        raise NotImplementedError("Scheduler.__init__")

    def add(self, req: Request) -> None:
        raise NotImplementedError("Scheduler.add")


    def schedule(self) -> dict[str, int]:
        raise NotImplementedError("Scheduler.schedule")

    def update(self, scheduled: dict[str, int]) -> list[str]:
        raise NotImplementedError("Scheduler.update")
