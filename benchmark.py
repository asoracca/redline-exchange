from __future__ import annotations

import argparse
import random
import time

from orderbook import LimitOrderBook, Side


def run(order_count: int, seed: int = 17) -> None:
    rng = random.Random(seed)
    book = LimitOrderBook("BENCH")
    started = time.perf_counter()
    trades = 0

    for i in range(order_count):
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        price = 10_000 + rng.randint(-20, 20)
        quantity = rng.randint(1, 500)
        trades += len(book.submit_limit(f"order-{i}", side, quantity, price))

    elapsed = time.perf_counter() - started
    rate = order_count / elapsed
    print(f"orders:        {order_count:,}")
    print(f"trades:        {trades:,}")
    print(f"active orders: {book.active_order_count():,}")
    print(f"elapsed:       {elapsed:.4f} seconds")
    print(f"throughput:    {rate:,.0f} orders/second")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--orders", type=int, default=100_000)
    args = parser.parse_args()
    if args.orders < 1:
        parser.error("--orders must be positive")
    run(args.orders)

