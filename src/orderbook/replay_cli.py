from __future__ import annotations

import argparse
from pathlib import Path

from .models import Side
from .replay import replay_csv


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay Redline order events from CSV")
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--symbol", default="REPLAY")
    parser.add_argument("--levels", type=int, default=5)
    args = parser.parse_args()
    if args.levels < 1:
        parser.error("--levels must be positive")

    result = replay_csv(args.csv_file, symbol=args.symbol)
    print(f"events: {result.events_processed:,}")
    print(f"trades: {len(result.trades):,}")
    print(f"active orders: {result.book.active_order_count():,}")
    print("bids:", result.book.depth(Side.BUY, levels=args.levels))
    print("asks:", result.book.depth(Side.SELL, levels=args.levels))


if __name__ == "__main__":
    main()
