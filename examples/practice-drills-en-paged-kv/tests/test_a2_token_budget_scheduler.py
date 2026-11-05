from drill import load

m = load("a2_token_budget_scheduler")


def make(budget=8, seqs=4, threshold=0):
    return m.Scheduler(token_budget=budget, max_num_seqs=seqs, long_prefill_threshold=threshold)


def test_small_prompt_prefills_in_one_step_then_decodes():
    s = make()
    s.add(m.Request("a", 5, 3))
    assert s.schedule() == {"a": 5}
    assert s.update({"a": 5}) == []
    assert s.schedule() == {"a": 1}


def test_long_prompt_is_chunked_across_steps():
    s = make(budget=8)
    s.add(m.Request("a", 20, 2))
    assert s.schedule() == {"a": 8}
    s.update({"a": 8})
    assert s.schedule() == {"a": 8}
    s.update({"a": 8})
    assert s.schedule() == {"a": 4}
    s.update({"a": 4})
    assert s.running[0].num_output_tokens == 1          # first token only after the last chunk


def test_running_requests_are_served_before_waiting_ones():
    s = make(budget=8)
    s.add(m.Request("a", 4, 5))
    s.update(s.schedule())                               # a is decoding now
    s.add(m.Request("b", 30, 1))
    assert s.schedule() == {"a": 1, "b": 7}


def test_max_num_seqs_limits_admission():
    s = make(budget=100, seqs=2)
    for r in "abc":
        s.add(m.Request(r, 3, 2))
    assert list(s.schedule()) == ["a", "b"]
    assert [r.req_id for r in s.waiting] == ["c"]


def test_fcfs_does_not_skip_a_blocked_request():
    s = make(budget=4, seqs=1)
    s.add(m.Request("big", 10, 1))
    s.add(m.Request("small", 1, 1))
    assert s.schedule() == {"big": 4}                    # small waits even though it would fit


def test_long_prefill_threshold_caps_chunks():
    s = make(budget=16, threshold=6)
    s.add(m.Request("a", 20, 1))
    s.add(m.Request("b", 3, 1))
    assert s.schedule() == {"a": 6, "b": 3}


def test_finished_requests_leave_running():
    s = make()
    s.add(m.Request("a", 2, 2))
    s.update(s.schedule())                               # prefill -> token 1
    assert s.update(s.schedule()) == ["a"]               # decode -> token 2 -> done
    assert s.running == []
    assert s.schedule() == {}


def test_budget_never_exceeded_over_a_long_run():
    s = make(budget=10, seqs=3, threshold=7)
    for i, (p, n) in enumerate([(13, 4), (2, 6), (25, 2), (1, 1), (9, 3)]):
        s.add(m.Request(f"r{i}", p, n))
    done = []
    for _ in range(60):
        sched = s.schedule()
        assert sum(sched.values()) <= 10
        assert len(s.running) <= 3
        done += s.update(sched)
    assert sorted(done) == [f"r{i}" for i in range(5)]
