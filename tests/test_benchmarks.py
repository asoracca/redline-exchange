import pytest
from orderbook import LimitOrderBook
from orderbook.workloads import WORKLOADS, generate, replay, workload_hash


@pytest.mark.parametrize("workload", WORKLOADS)
def test_workloads_are_reproducible_and_valid(workload):
    a, b = generate(400, 17, workload), generate(400, 17, workload)
    assert len(a) == 400 and a == b and workload_hash(a) == workload_hash(b)
    book = LimitOrderBook("BENCH")
    replay(book, a)
    book.assert_invariants()
