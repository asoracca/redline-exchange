from __future__ import annotations

import csv
import os
import subprocess
from pathlib import Path

import pytest

from orderbook import replay_csv


def _python_trades(path: Path) -> list[dict[str, str]]:
    result = replay_csv(path, symbol="REPLAY")
    return [
        {
            "sequence": str(trade.sequence),
            "symbol": trade.symbol,
            "price_ticks": str(trade.price_ticks),
            "quantity": str(trade.quantity),
            "maker_order_id": trade.maker_order_id,
            "taker_order_id": trade.taker_order_id,
            "taker_side": trade.taker_side.value,
        }
        for trade in result.trades
    ]


def _python_orders(path: Path) -> list[dict[str, str]]:
    result = replay_csv(path, symbol="REPLAY")
    return [
        {
            "order_id": order.order_id,
            "side": order.side.value,
            "quantity": str(order.quantity),
            "remaining": str(order.remaining),
            "sequence": str(order.sequence),
            "price_ticks": str(order.price_ticks),
        }
        for order in result.book.active_orders()
    ]


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def test_cpp_replay_matches_python_trade_and_book_state(tmp_path: Path):
    binary_text = os.environ.get("REDLINE_CPP_BINARY")
    if not binary_text:
        pytest.skip("set REDLINE_CPP_BINARY to a compiled redline_cpp executable")
    binary = Path(binary_text).resolve()
    events = Path("examples/parity_events.csv").resolve()
    trades = tmp_path / "cpp-trades.csv"
    orders = tmp_path / "cpp-orders.csv"

    subprocess.run(
        [
            str(binary),
            "replay",
            str(events),
            "--trades",
            str(trades),
            "--orders",
            str(orders),
        ],
        check=True,
    )

    assert _read_csv(trades) == _python_trades(events)
    assert _read_csv(orders) == _python_orders(events)
