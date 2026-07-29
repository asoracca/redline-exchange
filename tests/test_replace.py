import unittest

from orderbook import LimitOrderBook, Side


class ReplaceOrderTests(unittest.TestCase):
    def setUp(self):
        self.book = LimitOrderBook("TEST")

    def test_quantity_reduction_keeps_time_priority(self):
        self.book.submit_limit("first", Side.SELL, 10, 10_100)
        self.book.submit_limit("second", Side.SELL, 10, 10_100)

        self.book.replace("first", new_quantity=5)
        trades = self.book.submit_market("buyer", Side.BUY, 7)

        self.assertEqual(
            [(trade.maker_order_id, trade.quantity) for trade in trades],
            [("first", 5), ("second", 2)],
        )

    def test_quantity_increase_loses_time_priority(self):
        self.book.submit_limit("first", Side.SELL, 10, 10_100)
        self.book.submit_limit("second", Side.SELL, 10, 10_100)

        self.book.replace("first", new_quantity=15)
        trades = self.book.submit_market("buyer", Side.BUY, 12)

        self.assertEqual(
            [(trade.maker_order_id, trade.quantity) for trade in trades],
            [("second", 10), ("first", 2)],
        )

    def test_price_change_loses_priority_and_can_cross(self):
        self.book.submit_limit("bid", Side.BUY, 10, 10_000)
        self.book.submit_limit("ask", Side.SELL, 10, 10_100)

        trades = self.book.replace("ask", new_quantity=10, new_price_ticks=9_990)

        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price_ticks, 10_000)
        self.assertEqual(trades[0].maker_order_id, "bid")
        self.assertEqual(trades[0].taker_order_id, "ask")
        self.assertEqual(self.book.active_order_count(), 0)

    def test_repriced_order_does_not_reuse_stale_heap_priority(self):
        self.book.submit_limit("first", Side.SELL, 10, 10_100)
        self.book.submit_limit("second", Side.SELL, 10, 10_200)
        self.book.replace("first", new_quantity=10, new_price_ticks=10_300)

        trades = self.book.submit_market("buyer", Side.BUY, 15)

        self.assertEqual(
            [trade.maker_order_id for trade in trades],
            ["second", "first"],
        )

    def test_invalid_or_unknown_replace_is_rejected(self):
        with self.assertRaises(KeyError):
            self.book.replace("missing", 10)
        self.book.submit_limit("bid", Side.BUY, 10, 10_000)
        with self.assertRaises(ValueError):
            self.book.replace("bid", 0)
        with self.assertRaises(ValueError):
            self.book.replace("bid", 10, 0)

    def test_order_snapshots_cannot_mutate_the_book(self):
        self.book.submit_limit("bid", Side.BUY, 10, 10_000)
        snapshot = self.book.get_order("bid")
        snapshot.remaining = 1
        self.assertEqual(self.book.get_order("bid").remaining, 10)

    def test_order_ids_cannot_be_reused_after_cancel(self):
        self.book.submit_limit("bid", Side.BUY, 10, 10_000)
        self.book.cancel("bid")
        with self.assertRaises(ValueError):
            self.book.submit_limit("bid", Side.BUY, 10, 9_900)


if __name__ == "__main__":
    unittest.main()
