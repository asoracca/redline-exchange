"""Profile a prepared Python workload; profiler times are not benchmark results."""

import argparse
import cProfile
from datetime import datetime, timezone
import json
import platform
from pathlib import Path
import pstats
import tracemalloc

from orderbook import LimitOrderBook
from orderbook.workloads import WORKLOADS, generate, replay, workload_hash
from compare import source_hash


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--orders", type=int, default=20_000)
    p.add_argument("--seed", type=int, default=17)
    p.add_argument("--workload", choices=WORKLOADS, default="mixed")
    p.add_argument("--output", type=Path, default=Path("profile-results"))
    args = p.parse_args()
    if args.orders < 1:
        p.error("orders must be positive")
    events = generate(args.orders, args.seed, args.workload)
    args.output.mkdir(parents=True, exist_ok=True)
    book = LimitOrderBook("BENCH", retain_trade_history=False)
    profile = cProfile.Profile()
    profile.runcall(replay, book, events)
    profile.dump_stats(str(args.output / "matching.prof"))
    with (args.output / "profile.txt").open("w") as f:
        f.write(f"workload={args.workload} events={args.orders} seed={args.seed}\n")
        stats = pstats.Stats(profile, stream=f).strip_dirs()
        stats.sort_stats("cumulative").print_stats(25)
        stats.sort_stats("tottime").print_stats(25)
    report = args.output / "profile.txt"
    report.write_text(report.read_text().rstrip() + "\n")
    del book
    tracemalloc.start()
    book = LimitOrderBook("BENCH", retain_trade_history=False)
    replay(book, events)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    (args.output / "memory.txt").write_text(
        f"Python traced bytes (separate pass, prepared input excluded): retained={current}, peak={peak}\n"
        f"active_orders={book.active_order_count()}\n"
        "Not process RSS; no inference about native allocations.\n"
    )

    stats = pstats.Stats(profile)
    functions = [
        dict(
            file=Path(filename).name,
            line=line,
            function=function,
            calls=values[1],
            self_seconds=values[2],
            cumulative_seconds=values[3],
        )
        for (filename, line, function), values in stats.stats.items()
    ]
    data = dict(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=source_hash(),
        workload_sha256=workload_hash(events),
        workload=args.workload,
        count=args.orders,
        seed=args.seed,
        environment=dict(
            platform=platform.platform(), python=platform.python_version()
        ),
        retained_bytes=current,
        peak_bytes=peak,
        active_orders=book.active_order_count(),
        functions=sorted(functions, key=lambda f: f["self_seconds"], reverse=True),
    )
    (args.output / "profile.json").write_text(json.dumps(data, indent=2) + "\n")


if __name__ == "__main__":
    main()
