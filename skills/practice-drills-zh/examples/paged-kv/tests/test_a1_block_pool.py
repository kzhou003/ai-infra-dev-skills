import pytest

from drill import load

m = load("a1_block_pool")
BS = 4


def toks(n, start=0):
    return list(range(start, start + n))


def test_fresh_allocation_takes_blocks_from_the_front():
    pool = m.BlockPool(8, BS)
    blocks, cached = pool.allocate(toks(10))          # 2 full blocks + 1 partial
    assert blocks == [0, 1, 2]
    assert cached == 0
    assert pool.num_free_blocks == 5
    assert all(pool.ref_count(b) == 1 for b in blocks)


def test_only_full_blocks_are_cached():
    pool = m.BlockPool(8, BS)
    blocks, _ = pool.allocate(toks(10))
    h = m.hash_blocks(toks(10), BS)
    assert len(h) == 2
    assert pool.cached_block(h[0]) == blocks[0]
    assert pool.cached_block(h[1]) == blocks[1]


def test_shared_prefix_is_reused_while_running():
    pool = m.BlockPool(8, BS)
    a, _ = pool.allocate(toks(8) + [100, 101])
    b, cached = pool.allocate(toks(8) + [200])
    assert b[:2] == a[:2]
    assert cached == 8
    assert pool.ref_count(a[0]) == 2 and pool.ref_count(a[1]) == 2
    assert b[2] not in a


def test_prefix_must_match_from_the_start():
    pool = m.BlockPool(8, BS)
    pool.allocate(toks(8))
    _, cached = pool.allocate([999] + toks(7, 1))      # same second block tokens, different first block
    assert cached == 0


def test_freed_blocks_stay_cached_until_reused():
    pool = m.BlockPool(4, BS)
    a, _ = pool.allocate(toks(8))
    pool.free(a)
    assert pool.num_free_blocks == 4
    b, cached = pool.allocate(toks(8))
    assert b == a and cached == 8
    assert pool.num_free_blocks == 2


def test_free_is_reverse_order_so_tail_is_evicted_first():
    pool = m.BlockPool(3, BS)
    a, _ = pool.allocate(toks(12))                     # blocks 0,1,2 all full and cached
    pool.free(a)                                        # queue: 2, 1, 0 (tail first)
    h = m.hash_blocks(toks(12), BS)
    pool.allocate(toks(4, 500))                         # needs one fresh block -> evicts block 2
    assert pool.cached_block(h[2]) is None
    assert pool.cached_block(h[0]) == 0 and pool.cached_block(h[1]) == 1
    _, cached = pool.allocate(toks(8))                  # the head blocks 0,1 still hit
    assert cached == 8


def test_hit_on_free_block_reduces_capacity():
    pool = m.BlockPool(3, BS)
    a, _ = pool.allocate(toks(8))
    pool.free(a)                                        # 3 free, 2 of them cached
    # 8 cached tokens + 9 new tokens = 2 hits + 3 fresh blocks; only 1 free block is not a hit
    with pytest.raises(m.NoFreeBlocks):
        pool.allocate(toks(8) + toks(9, 50))


def test_failed_allocation_changes_nothing():
    pool = m.BlockPool(3, BS)
    a, _ = pool.allocate(toks(8))
    pool.free(a)
    before = (pool.num_free_blocks, [pool.ref_count(b) for b in range(3)])
    with pytest.raises(m.NoFreeBlocks):
        pool.allocate(toks(8) + toks(9, 50))
    assert (pool.num_free_blocks, [pool.ref_count(b) for b in range(3)]) == before
    _, cached = pool.allocate(toks(8))
    assert cached == 8


def test_eviction_removes_stale_hash():
    pool = m.BlockPool(2, BS)
    a, _ = pool.allocate(toks(4))
    h = m.hash_blocks(toks(4), BS)[0]
    pool.free(a)
    pool.allocate(toks(4, 50) + toks(4, 60))           # needs both blocks: evicts the cached one
    assert pool.cached_block(h) is None


def test_double_free_is_an_error():
    pool = m.BlockPool(2, BS)
    a, _ = pool.allocate(toks(4))
    pool.free(a)
    with pytest.raises(ValueError):
        pool.free(a)
