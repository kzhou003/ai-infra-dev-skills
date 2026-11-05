"""A1 · BlockPool with prefix caching — reference solution.

A fixed pool of KV-cache blocks shared by all requests (vLLM v1 `BlockPool` +
`FreeKVCacheBlockQueue`, simplified to one KV-cache group):

- Every block has a reference count. ref_cnt > 0: some running request uses it.
  ref_cnt == 0: it sits in the free queue and may be handed out again.
- A FULL block (block_size tokens) gets a content hash chained to the hash of the block
  before it, so equal hashes mean "same tokens AND same prefix". Freed blocks keep their hash:
  until a block is actually reused for something else it is a prefix-cache entry.
- allocate(token_ids) reuses the longest cached prefix, then takes fresh blocks from the
  FRONT of the free queue (least recently freed first). A fresh block that still carries an old
  hash is evicted from the cache at that moment.
- free(block_ids) decrements in REVERSE order and appends blocks that reach 0 to the BACK of the
  queue, so a sequence's tail blocks are evicted before its head blocks: heads are shared more.

API
    hash_blocks(token_ids, block_size) -> list[int]       given: one chained hash per full block
    NoFreeBlocks(Exception)                                 given
    BlockPool(num_blocks, block_size)
        .allocate(token_ids) -> (block_ids, num_cached_tokens)   all or nothing
        .free(block_ids) -> None
        .num_free_blocks -> int                            blocks with ref_cnt == 0
        .ref_count(block_id) -> int
        .cached_block(block_hash) -> int | None            block currently registered for a hash
"""
from __future__ import annotations

from collections import OrderedDict


class NoFreeBlocks(Exception):
    """Not enough evictable blocks for an allocation. Raised before anything is modified."""


def hash_blocks(token_ids: list[int], block_size: int) -> list[int]:
    """One hash per FULL block; block i's hash covers its tokens and the hash of block i-1.

    Chaining is what makes the cache a *prefix* cache: block 3 of two prompts only matches if
    blocks 0..2 matched too, because their hashes are inside block 3's hash.
    (Python's hash of a tuple of ints is deterministic, which is all a single process needs;
    vLLM uses sha256 or a seeded builtin hash for the same reason.)
    """
    hashes, parent = [], None
    for start in range(0, len(token_ids) - block_size + 1, block_size):
        parent = hash((parent, tuple(token_ids[start:start + block_size])))
        hashes.append(parent)
    return hashes


class BlockPool:
    def __init__(self, num_blocks: int, block_size: int) -> None:
        self.block_size = block_size
        self.ref = [0] * num_blocks                       # ref_cnt per block id
        self.block_hash: list[int | None] = [None] * num_blocks   # hash a block currently holds
        # Free queue in eviction order: front = evict first. An OrderedDict gives O(1)
        # popleft (popitem(last=False)), append, and O(1) removal from the MIDDLE, which a cache
        # hit on a free block needs. vLLM gets the same with an intrusive doubly-linked list
        # (prev/next pointers stored on the block objects) to avoid hashing on the hot path.
        self.free_q: OrderedDict[int, None] = OrderedDict((b, None) for b in range(num_blocks))
        self.cache: dict[int, int] = {}                   # block hash -> block id

    @property
    def num_free_blocks(self) -> int:
        return len(self.free_q)

    def ref_count(self, block_id: int) -> int:
        return self.ref[block_id]

    def cached_block(self, block_hash: int) -> int | None:
        return self.cache.get(block_hash)

    def allocate(self, token_ids: list[int]) -> tuple[list[int], int]:
        hashes = hash_blocks(token_ids, self.block_size)
        n_blocks = -(-len(token_ids) // self.block_size)     # ceil: a partial last block still needs a block

        # 1. Longest cached prefix. Stop at the FIRST miss: thanks to chaining, a later hit after a
        #    miss is impossible for honest hashes, and stopping keeps the blocks contiguous.
        hits: list[int] = []
        for h in hashes:
            b = self.cache.get(h)
            if b is None:
                break
            hits.append(b)
        need = n_blocks - len(hits)

        # 2. Capacity check BEFORE mutating anything (all-or-nothing). A hit on a block whose
        #    ref_cnt is 0 takes that block out of the free queue, so it no longer counts as free.
        hits_in_free = sum(1 for b in hits if self.ref[b] == 0)
        if self.num_free_blocks - hits_in_free < need:
            raise NoFreeBlocks(f"need {need} blocks, {self.num_free_blocks - hits_in_free} evictable")

        # 3. Touch the hits: ref 0 -> 1 removes the block from the eviction candidates.
        for b in hits:
            if self.ref[b] == 0:
                del self.free_q[b]
            self.ref[b] += 1

        # 4. Fresh blocks from the front of the queue (least recently freed). A block that still
        #    holds an old hash is evicted from the cache now, and only if the cache entry is still
        #    this block (another block may have been registered for that hash since).
        fresh: list[int] = []
        for _ in range(need):
            b, _ = self.free_q.popitem(last=False)
            old = self.block_hash[b]
            if old is not None and self.cache.get(old) == b:
                del self.cache[old]
            self.block_hash[b] = None
            self.ref[b] = 1
            fresh.append(b)

        # 5. Register the new FULL blocks in the cache. The partial last block gets no hash: its
        #    content will still change as tokens are appended. If the hash is already cached (two
        #    requests computed the same block), keep the existing entry: the first one wins.
        blocks = hits + fresh
        for i in range(len(hits), len(hashes)):
            h = hashes[i]
            self.block_hash[blocks[i]] = h
            self.cache.setdefault(h, blocks[i])
        return blocks, len(hits) * self.block_size

    def free(self, block_ids: list[int]) -> None:
        # Reverse order: the tail of a sequence is the least likely to be shared, so it should be
        # evicted first, i.e. sit nearer the FRONT of the queue. Appending tail-first does that.
        for b in reversed(block_ids):
            if self.ref[b] <= 0:
                raise ValueError(f"block {b} freed more times than allocated")
            self.ref[b] -= 1
            if self.ref[b] == 0:
                self.free_q[b] = None    # back of the queue; the hash (if any) stays cached
