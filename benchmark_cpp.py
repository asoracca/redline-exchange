from __future__ import annotations

import argparse
import csv
import random
import subprocess
import tempfile
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from orderbook import EventType, LimitOrderBook, read_events


@dataclass(frozen=True)
class ComparisonResult:
    implementation: str
    events: int
    trades: int
    active_orders: int
    elapsed_seconds: float
    throughput_per_second: float
    p50_microseconds: float
    p95_microseconds: float
    p99_microseconds: float


def generate_events(path: Path, order_count: int, seed: int) -> None:
    """Write one deterministic workload consumed by both implementations."""
    rng = random.Random(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["event_type", "order_id", "side", "quantity", "price_ticks"])
        for index in range(order_count):
            writer.writerow(
                [
                    "LIMIT",
                    f"order-{index}",
                    "BUY" if rng.random() < 0.5 else "SELL",
                    rng.randint(1, 500),
                    10_000 + rng.randint(-20, 20),
                ]
            )


def run_python(events_path: Path) -> ComparisonResult:
    events = read_events(events_path)
    book = LimitOrderBook("REPLAY", retain_trade_history=False)
    latencies_ns: list[int] = []
    trades = 0
    started = time.perf_counter()
    for event in events:
        operation_started = time.perf_counter_ns()
        if event.event_type is not EventType.LIMIT:
            raise ValueError("benchmark workload must contain only LIMIT events")
        produced = book.submit_limit(
            event.order_id,
            event.side,
            event.quantity,
            event.price_ticks,
        )
        latencies_ns.append(time.perf_counter_ns() - operation_started)
        trades += len(produced)
    elapsed = time.perf_counter() - started
    book.assert_invariants()
    latencies_ns.sort()
    return ComparisonResult(
        implementation="python",
        events=len(events),
        trades=trades,
        active_orders=book.active_order_count(),
        elapsed_seconds=elapsed,
        throughput_per_second=len(events) / elapsed,
        p50_microseconds=_percentile(latencies_ns, 0.50) / 1_000,
        p95_microseconds=_percentile(latencies_ns, 0.95) / 1_000,
        p99_microseconds=_percentile(latencies_ns, 0.99) / 1_000,
    )


def run_cpp(binary: Path, events_path: Path, result_path: Path) -> ComparisonResult:
    subprocess.run(
        [
            str(binary),
            "benchmark",
            str(events_path),
            "--csv",
            str(result_path),
        ],
        check=True,
    )
    with result_path.open(newline="", encoding="utf-8") as handle:
        row = next(csv.DictReader(handle))
    return ComparisonResult(
        implementation="cpp",
        events=int(row["events"]),
        trades=int(row["trades"]),
        active_orders=int(row["active_orders"]),
        elapsed_seconds=float(row["elapsed_seconds"]),
        throughput_per_second=float(row["throughput_per_second"]),
        p50_microseconds=float(row["p50_microseconds"]),
        p95_microseconds=float(row["p95_microseconds"]),
        p99_microseconds=float(row["p99_microseconds"]),
    )


def _percentile(values: list[int], probability: float) -> int:
    return values[round((len(values) - 1) * probability)]


def write_comparison(results: list[ComparisonResult], destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(results[0])))
        writer.writeheader()
        writer.writerows(asdict(result) for result in results)


def validate_same_work(events_path: Path, results: list[ComparisonResult]) -> None:
    python_result, cpp_result = results
    fields = ("events", "trades", "active_orders")
    for field in fields:
        if getattr(python_result, field) != getattr(cpp_result, field):
            raise RuntimeError(
                f"implementations disagree on {field} for {events_path}: "
                f"{getattr(python_result, field)} != {getattr(cpp_result, field)}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--orders", type=int, default=100_000)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--output", type=Path, default=Path("data/cpp_benchmark/comparison.csv")
    )
    args = parser.parse_args()
    if args.orders < 1:
        parser.error("--orders must be positive")

    with tempfile.TemporaryDirectory(prefix="redline-benchmark-") as temp_directory:
        events_path = Path(temp_directory) / "events.csv"
        cpp_path = Path(temp_directory) / "cpp.csv"
        generate_events(events_path, args.orders, args.seed)
        results = [
            run_python(events_path),
            run_cpp(args.binary, events_path, cpp_path),
        ]
        validate_same_work(events_path, results)
    write_comparison(results, args.output)
    for result in results:
        print(
            f"{result.implementation:>6}: {result.throughput_per_second:>12,.0f} "
            f"events/s | p50={result.p50_microseconds:>8.3f} us | "
            f"p95={result.p95_microseconds:>8.3f} us | "
            f"p99={result.p99_microseconds:>8.3f} us"
        )
    speedup = results[1].throughput_per_second / results[0].throughput_per_second
    print(f"C++ throughput speedup: {speedup:.2f}x")
    print(f"Saved comparison to {args.output}")


if __name__ == "__main__":
    main()
