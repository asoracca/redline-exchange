import unittest

from hypothesis import given, settings, strategies as st

from orderbook import LimitOrderBook, Side


operation = st.tuples(
    st.integers(min_value=0, max_value=3),
    st.booleans(),
    st.integers(min_value=1, max_value=100),
    st.integers(min_value=9_950, max_value=10_050),
)


class BookPropertyTests(unittest.TestCase):
    @settings(max_examples=100, deadline=None)
    @given(st.lists(operation, min_size=1, max_size=100))
    def test_random_event_sequences_preserve_invariants(self, operations):
        book = LimitOrderBook("FUZZ")
        next_order_id = 0

        for action, buy_side, quantity, price_ticks in operations:
            side = Side.BUY if buy_side else Side.SELL
            active = book.active_orders()

            if action == 0 or not active:
                book.submit_limit(f"limit-{next_order_id}", side, quantity, price_ticks)
                next_order_id += 1
            elif action == 1:
                selected = active[quantity % len(active)]
                book.cancel(selected.order_id)
            elif action == 2:
                selected = active[quantity % len(active)]
                book.replace(selected.order_id, quantity, price_ticks)
            else:
                book.submit_market(f"market-{next_order_id}", side, quantity)
                next_order_id += 1

            book.assert_invariants()


if __name__ == "__main__":
    unittest.main()
