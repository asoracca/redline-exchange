import unittest

from orderbook import LimitOrderBook, Side


class LimitOrderBookTests(unittest.TestCase):
    def setUp(self):
        self.book = LimitOrderBook("TEST")

    def test_non_crossing_limits_rest(self):
        self.book.submit_limit("bid", Side.BUY, 100, 9_900)
        self.book.submit_limit("ask", Side.SELL, 50, 10_100)
        top = self.book.top_of_book()
        self.assertEqual(top["bid"].price_ticks, 9_900)
        self.assertEqual(top["ask"].price_ticks, 10_100)
        self.assertEqual(self.book.spread_ticks(), 200)

    def test_crossing_order_executes_at_resting_price(self):
        self.book.submit_limit("ask", Side.SELL, 100, 10_100)
        trades = self.book.submit_limit("buy", Side.BUY, 40, 10_200)
        self.assertEqual(len(trades), 1)
        self.assertEqual(trades[0].price_ticks, 10_100)
        self.assertEqual(trades[0].quantity, 40)
        self.assertEqual(self.book.get_order("ask").remaining, 60)

    def test_price_priority(self):
        self.book.submit_limit("ask-high", Side.SELL, 10, 10_200)
        self.book.submit_limit("ask-low", Side.SELL, 10, 10_100)
        trades = self.book.submit_market("buyer", Side.BUY, 15)
        self.assertEqual(
            [trade.maker_order_id for trade in trades], ["ask-low", "ask-high"]
        )
        self.assertEqual([trade.quantity for trade in trades], [10, 5])

    def test_time_priority_at_same_price(self):
        self.book.submit_limit("first", Side.SELL, 10, 10_100)
        self.book.submit_limit("second", Side.SELL, 10, 10_100)
        trades = self.book.submit_market("buyer", Side.BUY, 15)
        self.assertEqual(
            [trade.maker_order_id for trade in trades], ["first", "second"]
        )

    def test_market_remainder_does_not_rest(self):
        self.book.submit_limit("ask", Side.SELL, 10, 10_100)
        trades = self.book.submit_market("buyer", Side.BUY, 25)
        self.assertEqual(sum(trade.quantity for trade in trades), 10)
        self.assertIsNone(self.book.get_order("buyer"))
        self.assertEqual(self.book.active_order_count(), 0)

    def test_cancel_removes_liquidity(self):
        self.book.submit_limit("bid", Side.BUY, 100, 10_000)
        canceled = self.book.cancel("bid")
        self.assertEqual(canceled.remaining, 100)
        self.assertIsNone(self.book.top_of_book()["bid"])
        with self.assertRaises(KeyError):
            self.book.cancel("bid")

    def test_depth_aggregates_price_levels(self):
        self.book.submit_limit("bid-1", Side.BUY, 100, 10_000)
        self.book.submit_limit("bid-2", Side.BUY, 50, 10_000)
        self.book.submit_limit("bid-3", Side.BUY, 75, 9_990)
        levels = self.book.depth(Side.BUY)
        self.assertEqual(levels[0].quantity, 150)
        self.assertEqual(levels[0].order_count, 2)
        self.assertEqual(levels[1].price_ticks, 9_990)

    def test_rejects_invalid_and_duplicate_active_orders(self):
        with self.assertRaises(ValueError):
            self.book.submit_limit("bad", Side.BUY, 0, 10_000)
        self.book.submit_limit("same", Side.BUY, 10, 10_000)
        with self.assertRaises(ValueError):
            self.book.submit_limit("same", Side.BUY, 10, 9_900)


if __name__ == "__main__":
    unittest.main()
