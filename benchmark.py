from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from pathlib import Path
import random
import time

from orderbook import LimitOrderBook, Side


@dataclass(frozen=True)
class BenchmarkResult:
    orders: int
    trades: int
    active_orders: int
    elapsed_seconds: float
    throughput_per_second: float
    p50_microseconds: float
    p95_microseconds: float


def run(order_count: int, seed: int = 17) -> BenchmarkResult:
    """Benchmark randomized crossing limit orders with reproducible input."""
    if order_count < 1:
        raise ValueError("order_count must be positive")

    rng = random.Random(seed)
    book = LimitOrderBook("BENCH", retain_trade_history=False)
    latencies_ns: list[int] = []
    trades = 0
    started = time.perf_counter()

    for index in range(order_count):
        side = Side.BUY if rng.random() < 0.5 else Side.SELL
        price = 10_000 + rng.randint(-20, 20)
        quantity = rng.randint(1, 500)
        operation_started = time.perf_counter_ns()
        produced = book.submit_limit(f"order-{index}", side, quantity, price)
        latencies_ns.append(time.perf_counter_ns() - operation_started)
        trades += len(produced)

    elapsed = time.perf_counter() - started
    latencies_ns.sort()
    return BenchmarkResult(
        orders=order_count,
        trades=trades,
        active_orders=book.active_order_count(),
        elapsed_seconds=elapsed,
        throughput_per_second=order_count / elapsed,
        p50_microseconds=_percentile(latencies_ns, 0.50) / 1_000,
        p95_microseconds=_percentile(latencies_ns, 0.95) / 1_000,
    )


def _percentile(values: list[int], percentile: float) -> int:
    index = round((len(values) - 1) * percentile)
    return values[index]


def _print_results(results: list[BenchmarkResult]) -> None:
    print(
        f"{'orders':>10} {'trades':>10} {'active':>10} {'seconds':>10} "
        f"{'orders/s':>12} {'p50 us':>10} {'p95 us':>10}"
    )
    for result in results:
        print(
            f"{result.orders:>10,} {result.trades:>10,} "
            f"{result.active_orders:>10,} {result.elapsed_seconds:>10.3f} "
            f"{result.throughput_per_second:>12,.0f} "
            f"{result.p50_microseconds:>10.2f} {result.p95_microseconds:>10.2f}"
        )


def _write_csv(results: list[BenchmarkResult], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(results[0])))
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--orders",
        type=int,
        nargs="+",
        default=[10_000, 100_000, 1_000_000],
        help="one or more workload sizes",
    )
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    if any(value < 1 for value in args.orders):
        parser.error("--orders values must be positive")

    benchmark_results = [run(value, args.seed) for value in args.orders]
    _print_results(benchmark_results)
    if args.csv:
        _write_csv(benchmark_results, args.csv)
