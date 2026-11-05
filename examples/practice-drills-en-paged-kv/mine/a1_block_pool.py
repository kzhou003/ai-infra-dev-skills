"""A1 · BlockPool with prefix caching — your implementation (run ./check.sh a1).

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
        raise NotImplementedError("BlockPool.__init__")

    @property
    def num_free_blocks(self) -> int:
        return len(self.free_q)

    def ref_count(self, block_id: int) -> int:
        return self.ref[block_id]

    def cached_block(self, block_hash: int) -> int | None:
        return self.cache.get(block_hash)

    def allocate(self, token_ids: list[int]) -> tuple[list[int], int]:
        raise NotImplementedError("BlockPool.allocate")

    def free(self, block_ids: list[int]) -> None:
        # Reverse order: the tail of a sequence is the least likely to be shared, so it should be
        # evicted first, i.e. sit nearer the FRONT of the queue. Appending tail-first does that.
        raise NotImplementedError("BlockPool.free")
