lede: Why an LLM server stores the KV cache in fixed-size blocks, how blocks become a prefix cache, and how a scheduler decides which tokens run in each step.
# Paged KV cache and continuous batching

## The problem: KV memory is the bottleneck

A decoder-only model keeps, for every token it has seen, a key and a value vector per layer: the **KV cache**. For a 8B model in bf16 that is on the order of 128 KB per token, so a single 32k-token conversation needs gigabytes. Three facts shape everything else:

| Fact | Consequence |
|---|---|
| Sequence lengths are unknown up front (the model decides when to stop) | Reserving `max_len` per request wastes most of the memory |
| Many requests share prefixes (system prompts, few-shot examples, multi-turn chats) | Recomputing and storing the same prefix twice wastes compute and memory |
| GPU throughput needs large batches, but requests arrive and finish at different times | Batches must be rebuilt every step, not once per batch |

### The fix: allocate in blocks, like virtual memory

vLLM's PagedAttention splits each sequence's KV cache into fixed-size **blocks** (16 tokens by default). A request owns a list of block ids, its *block table*; blocks of one request need not be contiguous. Memory is allocated one block at a time as the sequence grows, so waste is at most one partially filled block per request.

::: flow A block table maps a sequence onto scattered blocks
cfg cw=170 rh=86 nw=146
n seq 0 0.5 "request A" "40 tokens" k=dark
n t0 1 0 "tokens 0–15" "logical block 0" k=vio
n t1 1 1 "tokens 16–31" "logical block 1" k=vio
n t2 1 2 "tokens 32–39" "logical block 2" k=vio
n p7 3 0 "block 7" "full" k=acc
n p2 3 1 "block 2" "full" k=acc
n p5 3 2 "block 5" "8 / 16 used" k=warn
e seq -> t0
e seq -> t1
e seq -> t2
e t0 -> p7 "table[0]"
e t1 -> p2 "table[1]"
e t2 -> p5 "table[2]"
cap: The attention kernel reads K/V through the block table, so physical blocks can live anywhere in the pool. Only the last block can be partly empty.
:::

::: callout analogy A library with fixed-size shelves
Instead of reserving a whole bookcase for every reader "in case they borrow a lot", the library hands out one shelf at a time and keeps a card (the block table) saying which shelves belong to whom. A reader's shelves can be anywhere in the building. When two readers want the same reference books, the librarian points both cards at the same shelf and counts how many cards point there (the reference count).
:::

## Prefix caching: blocks as cache entries

Because a full block's content never changes, it can be identified by a hash of its tokens. vLLM chains the hashes, so block *i*'s hash also covers the hash of block *i-1* ([[vllm:vllm/v1/core/kv_cache_utils.py@hash_block_tokens|hash_block_tokens]]). Two requests share block *i* only if they agree on every token up to the end of that block, which is exactly the condition for the KV values to be identical.

::: flow Chained block hashes
cfg cw=196 rh=86 nw=170
n b0 0 0 "block 0 tokens" "system prompt" k=vio
n b1 1 0 "block 1 tokens" "few-shot example" k=vio
n b2 2 0 "block 2 tokens" "user question" k=vio
n h0 0 1 "h0 = H(None, b0)" "" k=acc
n h1 1 1 "h1 = H(h0, b1)" "" k=acc
n h2 2 1 "h2 = H(h1, b2)" "" k=acc
e b0 -> h0
e b1 -> h1
e b2 -> h2
e h0 -> h1 k=acc
e h1 -> h2 k=acc
cap: The blue arrows are the parent links. Change one token in block 0 and every later hash changes too, so a cache lookup can stop at the first miss.
:::

The pool keeps a `hash → block` map. The important trick is what happens on free ([[vllm:vllm/v1/core/block_pool.py@BlockPool.free_blocks|BlockPool.free_blocks]]): a block whose reference count drops to 0 goes to the back of a **free queue** but *keeps its hash*. It is now both free memory and a cache entry. Only when the block is taken from the front of the queue for new content is its hash evicted ([[vllm:vllm/v1/core/block_pool.py@BlockPool._maybe_evict_cached_block|_maybe_evict_cached_block]]). A cache hit on a free block simply takes it back out of the queue ([[vllm:vllm/v1/core/block_pool.py@BlockPool.touch|touch]]).

::: callout key Free queue = LRU order
The free queue ([[vllm:vllm/v1/core/kv_cache_utils.py@FreeKVCacheBlockQueue|FreeKVCacheBlockQueue]]) is ordered by eviction priority: front evicted first. Requests free their blocks **in reverse** ([[vllm:vllm/v1/core/single_type_kv_cache_manager.py#L179|single_type_kv_cache_manager.py]]), so a sequence's tail, the part least likely to be shared, is evicted before its head. Drill A1 builds exactly this.
:::

## Continuous batching: one token budget per step

Each engine step runs one forward pass over a batch. The v1 scheduler ([[vllm:vllm/v1/core/sched/scheduler.py@Scheduler.schedule|Scheduler.schedule]]) does not distinguish "prefill" and "decode" requests. Every request has `num_tokens` (prompt + generated) and `num_computed_tokens` (already in the KV cache), and the scheduler hands out up to `max_num_scheduled_tokens` new tokens per step:

::: flow One scheduling step
cfg cw=196 rh=92 nw=170
n budget 0 0.5 "token budget" "e.g. 8192 tokens" k=dark
n run 1 0 "1. RUNNING first" "decode = 1 token each" k=pass
n wait 1 1 "2. WAITING, FCFS" "prompt chunks" k=warn
n cap 2 1 "long-prefill cap" "threshold per request" k=todo
n out 3 0.5 "this step's batch" "req → num tokens" k=acc
e budget -> run
e budget -> wait
e wait -> cap
e run -> out
e cap -> out
cap: Running requests are served first ([[vllm:vllm/v1/core/sched/scheduler.py#L209|L209]]), then waiting ones while budget and `max_num_seqs` allow ([[vllm:vllm/v1/core/sched/scheduler.py#L348|L348]]). A long prompt is split across steps: **chunked prefill**.
:::

Why this design:

- **Decodes first** keeps inter-token latency steady: a running request already holds KV memory, and stalling it wastes that memory.
- **Chunked prefill** lets a 30k-token prompt enter without freezing all decoding requests for a whole step; the optional long-prefill threshold caps how much of the step one prompt can take.
- **FCFS without skipping** prevents starvation: if the head of the waiting queue cannot be admitted, smaller requests behind it wait too.

::: callout analogy A kitchen with a fixed number of burners per minute
Every minute (step) the kitchen has a fixed number of burner-slots (token budget). Dishes already cooking (running requests) need one slot to finish their next stage; they go first so nothing burns. New orders (waiting requests) get the remaining slots in arrival order; a banquet order is cooked in several rounds rather than blocking the kitchen.
:::

## Where the drills fit

| Drill | Rebuilds | Source |
|---|---|---|
| A1 BlockPool | ref counts, LRU free queue, chained-hash prefix cache, all-or-nothing allocation | [[vllm:vllm/v1/core/block_pool.py@BlockPool|block_pool.py]] |
| A2 Scheduler step | token budget, running-first, FCFS admission, chunked prefill, long-prefill cap | [[vllm:vllm/v1/core/sched/scheduler.py@Scheduler.schedule|scheduler.py]] |
