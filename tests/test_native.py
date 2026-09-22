"""Exact behavioral parity, including inherited reference-engine regressions."""

import pytest
from hypothesis import given, settings, strategies as st

pytest.importorskip("orderbook._native")

import test_book
import test_replace
from orderbook import LimitOrderBook, Side
from orderbook.native import NativeLimitOrderBook, MAX_VALUE
from orderbook.workloads import WORKLOADS, apply, generate, verify


class TestNativeBook(test_book.LimitOrderBookTests):
    def setUp(self):
        self.book = NativeLimitOrderBook("TEST")


class TestNativeReplace(test_replace.ReplaceOrderTests):
    def setUp(self):
        self.book = NativeLimitOrderBook("TEST")


@pytest.mark.parametrize("workload", WORKLOADS)
@pytest.mark.parametrize("seed", [0, 17, 42])
def test_workload_parity(workload, seed):
    verify(NativeLimitOrderBook, generate(1000, seed, workload))


@settings(max_examples=100, deadline=None)
@given(
    st.lists(
        st.tuples(
            st.integers(0, 3),
            st.booleans(),
            st.integers(1, 100),
            st.integers(9950, 10050),
        ),
        min_size=1,
        max_size=100,
    )
)
def test_every_event_state(operations):
    py, cpp = LimitOrderBook("TEST"), NativeLimitOrderBook("TEST")
    for i, (op, buy, qty, price) in enumerate(operations):
        side = Side.BUY if buy else Side.SELL
        active = py.active_orders()
        if op == 0 or not active:
            event = ("submit_limit", str(i), side, qty, price)
        elif op == 1:
            event = ("cancel", active[qty % len(active)].order_id)
        elif op == 2:
            event = ("replace", active[qty % len(active)].order_id, qty, price)
        else:
            event = ("submit_market", str(i), side, qty)
        assert apply(py, event) == apply(cpp, event)
        assert py.active_orders() == cpp.active_orders()
        assert py.trade_history() == cpp.trade_history()
        assert py.top_of_book() == cpp.top_of_book()
        for s in Side:
            assert py.depth(s, 100) == cpp.depth(s, 100)
        py.assert_invariants()
        cpp.assert_invariants()


def test_native_bounds_and_atomic_rejection():
    book = NativeLimitOrderBook("TEST")
    book.submit_limit("a", Side.SELL, MAX_VALUE, MAX_VALUE)
    book.submit_market("m", Side.BUY, MAX_VALUE - 1)
    before = book.active_orders()
    with pytest.raises(ValueError):
        book.replace("a", MAX_VALUE)
    assert book.active_orders() == before
    with pytest.raises(ValueError):
        book.submit_limit("b", Side.BUY, 1, MAX_VALUE + 1)
    book.submit_limit("b", Side.BUY, 1, 1)


def test_trade_history_disabled():
    book = NativeLimitOrderBook("TEST", retain_trade_history=False)
    book.submit_limit("a", Side.SELL, 10, 10)
    assert len(book.submit_market("b", Side.BUY, 2)) == 1
    assert book.trade_history() == ()
