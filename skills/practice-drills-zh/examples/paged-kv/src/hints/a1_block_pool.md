lede: A fixed pool of KV blocks shared by all requests: reference counts decide who owns a block, an LRU free queue decides which block is reused, and chained hashes turn freed blocks into a prefix cache.
# A1 · BlockPool: ref counts, LRU free queue, prefix cache

## The drill in one minute

- **Where it lives**: every engine step, the KV-cache manager asks the pool for blocks for new tokens and returns blocks of finished requests. In vLLM v1 this is [[vllm:vllm/v1/core/block_pool.py@BlockPool|BlockPool]].
- **You implement**: `BlockPool.__init__`, `allocate(token_ids) -> (block_ids, num_cached_tokens)` and `free(block_ids)`. `hash_blocks`, `NoFreeBlocks` and the three read-only accessors are given.
- **The rules that make it subtle**:
  1. A cache hit on a block with `ref_cnt == 0` takes that block **out of the free queue**: it is no longer free capacity.
  2. `allocate` is **all or nothing**: check capacity before touching any state.
  3. Fresh blocks come from the **front** of the queue; a fresh block that still holds an old hash is **evicted** from the cache right then.
  4. `free` decrements in **reverse** order and appends ref-0 blocks to the **back**; their hashes stay cached.

**The tests check**: fresh allocation order · only full blocks are cached · sharing while running · prefix must match from block 0 · freed blocks still hit · reverse free evicts the tail first · hits on free blocks reduce capacity · failure changes nothing · eviction removes the stale hash · double free raises.

## Intuition

::: callout analogy Hotel rooms with a memory
Each block is a hotel room. `ref_cnt` is how many guests share it. When the last guest checks out, the room goes to the end of the "available" line **but housekeeping does not clean it yet**: if a returning guest asks for "the room with exactly my things in it" (same hash), they get it back instantly. Only when the front desk gives that room to a *new* guest is it cleaned (the old hash evicted). And when a family leaves, the kids' rooms (the tail) are put in line ahead of the parents' room (the head), because the parents' room is the one other relatives are likely to ask for again.
:::

## The data structures

::: flow Three structures, one invariant
cfg cw=200 rh=96 nw=176
n ref 0 0 "ref[block]" "who uses it now" k=vio
n fq 1.7 0 "free queue (LRU)" "ref == 0, front = evict" k=warn
n bh 0 1.4 "block_hash[block]" "hash it holds, or None" k=acc
n cache 1.7 1.4 "cache: hash → block" "full blocks only" k=teal
e ref -> fq "ref → 0: append"
e fq:b -> cache:t "pop: evict old hash" k=teal
e bh -> cache "full blocks"
cap: Invariant: a block is in the free queue **iff** its ref count is 0. The cache may point at free blocks; that is the whole point.
:::

## Step through one scenario

::: steps Pool of 4 blocks, block_size 4
::: flow
cfg cw=150 rh=80 nw=122
n q 0 0 "free queue" "front → back" k=warn
n b0 1 0 "block 0" "" k=acc
n b1 2 0 "block 1" "" k=acc
n b2 3 0 "block 2" "" k=acc
n b3 4 0 "block 3" "" k=acc
n c 2 1 "cache" "hash → block" k=teal
e q -> b0
e b0 -> b1 dash
e b1 -> b2 dash
e b2 -> b3 dash
e b0:b -> c:l "h0"
e b1:b -> c:t "h1"
:::
--- step Start {hl=q,b0,b1,b2,b3}
All four blocks are free, in id order: queue `0 1 2 3`. Cache empty. {{cells: on:0 on:1 on:2 on:3}}
--- step allocate(A = 10 tokens) {hl=b0,b1,b2}
`hash_blocks` gives 2 hashes (two full blocks; the last 2 tokens are a partial block). No hits. Need ⌈10/4⌉ = 3 blocks → pop `0 1 2` from the front. Register `h0 → 0`, `h1 → 1`; block 2 gets no hash. Queue: `3`. {{cells: t:0 t:1 t:2 _:3}}
--- step allocate(B = A's first 8 tokens + 1 new) {hl=b0,b1,c}
Hashes of B: `h0, h1` → both hit (blocks 0, 1, ref becomes 2). Need 3 − 2 = 1 fresh block → pop `3`. B = `[0, 1, 3]`, `num_cached_tokens = 8`. Queue empty.
--- step free(A) {hl=b2,q}
Reverse order: block 2 → ref 0 → append; block 1 → ref 1; block 0 → ref 1. Queue: `2`. Blocks 0 and 1 are still used by B.
--- step free(B) {hl=q,b3,b1,b0}
Reverse: 3 → 0 (append), 1 → 0 (append), 0 → 0 (append). Queue: `2 3 1 0`. **Tail first**: the shared head (block 0) is the last to be evicted. Cache still holds `h0 → 0`, `h1 → 1`. {{cells: _:2 _:3 h:1 h:0}}
--- step allocate(A again) {hl=b0,b1,c}
Hits `h0 → 0`, `h1 → 1`, both have ref 0, so both leave the queue (capacity drops by 2). Need 1 fresh → pop `2` (front). Queue: `3`. Prefix caching saved 8 tokens of prefill.
:::

## Pitfalls

- **Counting hits on free blocks as free capacity.** With 3 free blocks of which 2 are hits, a request that needs 3 fresh blocks must fail. A naive check passes and then crashes popping an empty queue, leaving refs incremented.
- **Mutating before the capacity check.** Touching hits first and raising later leaks references: those blocks can never be freed.
- **Forgetting to evict the stale hash** when a block is reused: the cache then maps an old hash to a block with new content, and a later "hit" returns wrong KV values silently.
- **Evicting the wrong entry**: only delete `cache[old]` if it still points at *this* block.
- **Caching the partial last block**: its content changes as tokens are appended.
- **Freeing in forward order**: correct refcounts, wrong eviction order. The test with a 3-block pool catches it.

## Hints

::: hint 1 I/O examples and the key questions
```python
pool = BlockPool(num_blocks=4, block_size=4)
pool.allocate(list(range(10)))        # -> ([0, 1, 2], 0)
pool.allocate(list(range(8)) + [99])  # -> ([0, 1, 3], 8)    blocks 0,1 shared, ref 2
pool.num_free_blocks                  # -> 0
pool.allocate([7])                    # raises NoFreeBlocks, nothing changes
```

#### Key questions

1. Which data structure gives O(1) "pop the oldest", "append newest" **and** "remove this one from the middle"?
2. A cache hit on a block whose `ref_cnt` is 0: what has to happen to the free queue?
3. How many blocks does a 10-token sequence need with `block_size = 4`, and how many of them get a hash?
4. When exactly is a hash removed from the cache?
5. Why reverse order in `free`?
:::

::: hint 2 Approach and common traps
- **State**: `ref: list[int]`, `block_hash: list[int | None]`, `free_q: OrderedDict[int, None]` (front = evict first), `cache: dict[int, int]`.
- **allocate**:
  1. `hashes = hash_blocks(...)`, `n = ceil(len / block_size)`.
  2. Walk `hashes` while `cache` has them → `hits`. Stop at the first miss.
  3. `need = n - len(hits)`; `evictable = len(free_q) - (#hits with ref 0)`; raise if `evictable < need`.
  4. Touch hits (remove from `free_q` if ref was 0; `ref += 1`).
  5. Pop `need` blocks from the front; evict their old hash if `cache[old] == block`; set ref 1.
  6. Give hashes to the new full blocks (`setdefault`, first writer wins).
- **free**: `for b in reversed(ids)`: decrement; at 0 append to the back. Raise on ref ≤ 0.
:::

::: hint 3 Detailed answers
::: answer Answers to the key questions
1. An `OrderedDict` keyed by block id: `popitem(last=False)`, `d[b] = None`, `del d[b]` are all O(1). vLLM uses an intrusive doubly-linked list on the block objects for the same complexity without hashing ([[vllm:vllm/v1/core/kv_cache_utils.py@FreeKVCacheBlockQueue|FreeKVCacheBlockQueue]]).
2. It must be removed from the free queue (it is in use again), which is why it does not count as free capacity for the same allocation.
3. ⌈10/4⌉ = 3 blocks; only the 2 full blocks get a hash.
4. When the block is popped from the free queue to hold *new* content (and only if the cache entry still points at that block). Freeing never removes hashes.
5. The free queue is the eviction order. Appending tail blocks first puts them nearer the front, so they are evicted before the head blocks, which are the ones other requests are most likely to share.
:::
:::

## Reference solution

::: solution solutions/a1_block_pool.py
{{code: solutions/a1_block_pool.py}}
:::

## Follow-ups and the real source

- vLLM keeps one more rule this drill skips: it never serves the *whole* prompt from cache, it recomputes at least the last token so the model produces logits for sampling. Where would you add that?
- How does the pool change when a model has several KV-cache groups (e.g. sliding-window + full attention layers)? Look at [[vllm:vllm/v1/core/kv_cache_coordinator.py|kv_cache_coordinator.py]].
- Compare with the real code: [[vllm:vllm/v1/core/block_pool.py@BlockPool.get_new_blocks|get_new_blocks]] · [[vllm:vllm/v1/core/block_pool.py@BlockPool.touch|touch]] · [[vllm:vllm/v1/core/block_pool.py@BlockPool.free_blocks|free_blocks]] · [[vllm:vllm/v1/core/block_pool.py@BlockPool.cache_full_blocks|cache_full_blocks]].
