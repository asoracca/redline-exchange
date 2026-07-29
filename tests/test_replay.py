import unittest
from io import StringIO

from orderbook import Side, read_events, replay_csv

EVENTS = """event_type,order_id,side,quantity,price_ticks
LIMIT,ask-1,SELL,10,10100
LIMIT,ask-2,SELL,10,10100
REPLACE,ask-1,,5,
MARKET,buyer,BUY,7,
CANCEL,ask-2,,,
"""


class ReplayTests(unittest.TestCase):
    def test_csv_replay_preserves_event_and_trade_order(self):
        result = replay_csv(StringIO(EVENTS), symbol="TEST")

        self.assertEqual(result.events_processed, 5)
        self.assertEqual(
            [(trade.maker_order_id, trade.quantity) for trade in result.trades],
            [("ask-1", 5), ("ask-2", 2)],
        )
        self.assertEqual(result.book.active_order_count(), 0)
        result.book.assert_invariants()

    def test_same_csv_reconstructs_identical_book(self):
        first = replay_csv(StringIO(EVENTS), symbol="TEST")
        second = replay_csv(StringIO(EVENTS), symbol="TEST")

        self.assertEqual(first.trades, second.trades)
        self.assertEqual(first.book.depth(Side.BUY), second.book.depth(Side.BUY))
        self.assertEqual(first.book.depth(Side.SELL), second.book.depth(Side.SELL))

    def test_parser_reports_the_bad_line(self):
        bad = StringIO(
            "event_type,order_id,side,quantity,price_ticks\n"
            "LIMIT,bid,NOT_A_SIDE,10,10000\n"
        )
        with self.assertRaisesRegex(ValueError, "CSV line 2"):
            read_events(bad)

    def test_replay_reports_the_failing_event(self):
        bad = StringIO(
            "event_type,order_id,side,quantity,price_ticks\nCANCEL,missing,,,\n"
        )
        with self.assertRaisesRegex(ValueError, "event 1"):
            replay_csv(bad)


if __name__ == "__main__":
    unittest.main()
