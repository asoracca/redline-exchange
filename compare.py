"""Repeated Python/API-to-C++ benchmarks with untimed exact parity checks."""

import argparse
import importlib.metadata
import importlib.util
import os
from collections import Counter
import csv
from datetime import datetime, timezone
import gc
import hashlib
import json
import math
from pathlib import Path
import platform
import statistics
import time

from orderbook import LimitOrderBook
from orderbook.build_info import validate_native_build
from orderbook.workloads import (
    WORKLOADS,
    apply,
    generate,
    replay,
    verify,
    workload_hash,
)

ROOT = Path(__file__).resolve().parent


def percentile(values, q):
    return sorted(values)[max(0, math.ceil(len(values) * q) - 1)] / 1000


def measure(factory, events):
    # Throughput and latency use distinct fresh books. Workload construction,
    # equality checks, book destruction, and report writing are all untimed.
    gc.collect()
    book = factory("BENCH", retain_trade_history=False)
    start = time.perf_counter_ns()
    trades = replay(book, events)
    elapsed = (time.perf_counter_ns() - start) / 1e9
    active = book.active_order_count()
    del book
    gc.collect()
    book = factory("BENCH", retain_trade_history=False)
    latencies = []
    by_operation = {}
    for event in events:
        start = time.perf_counter_ns()
        apply(book, event)
        duration = time.perf_counter_ns() - start
        latencies.append(duration)
        by_operation.setdefault(event[0], []).append(duration)
    return dict(
        elapsed_seconds=elapsed,
        events_per_second=len(events) / elapsed,
        p50_us=percentile(latencies, 0.50),
        p95_us=percentile(latencies, 0.95),
        p99_us=percentile(latencies, 0.99),
        trades=trades,
        active_orders=active,
        operation_latency={
            op: {f"p{int(q * 100)}_us": percentile(v, q) for q in [0.5, 0.95, 0.99]}
            for op, v in by_operation.items()
        },
    )


def source_hash():
    digest = hashlib.sha256()
    files = [
        ROOT / "compare.py",
        ROOT / "study.py",
        ROOT / "profile_matching.py",
        *sorted((ROOT / "src/orderbook").glob("*.py")),
        *sorted((ROOT / "cpp").glob("*")),
        ROOT / "scripts/build_native.py",
    ]
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def report(data, output, chart=True):
    output.mkdir(parents=True, exist_ok=True)
    (output / "results.json").write_text(json.dumps(data, indent=2) + "\n")
    rows = []
    for result in data["runs"]:
        rows.append({k: v for k, v in result.items() if k != "operation_latency"})
    with (output / "results.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Measured API performance",
        "",
        "Median of repeated runs; latency is measured in a separate pass. "
        "C++ includes the Python binding and conversion to the same Python value objects.",
        "",
        "| Workload | Backend | Events/s | Trial min–max | p50 µs | p95 µs | p99 µs |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    summaries = []
    for workload in data["workloads"]:
        for backend in data["backends"]:
            group = [
                r for r in rows if r["workload"] == workload and r["backend"] == backend
            ]
            s = {
                k: statistics.median(r[k] for r in group)
                for k in ["events_per_second", "p50_us", "p95_us", "p99_us"]
            }
            s["min"] = min(r["events_per_second"] for r in group)
            s["max"] = max(r["events_per_second"] for r in group)
            summaries.append((workload, backend, s))
            lines.append(
                f"| {workload} | {backend} | {s['events_per_second']:,.0f} | "
                f"{s['min']:,.0f}–{s['max']:,.0f} | {s['p50_us']:.2f} | {s['p95_us']:.2f} | {s['p99_us']:.2f} |"
            )
    lines += [
        "",
        "Events/s equals orders/s only for crossing/resting (all submissions).",
        "",
        f"Environment: {data['environment']['platform']}; Python {data['environment']['python']}.",
        f"Events per workload: {data['count']:,}; seed: {data['seed']}; repeats: {data['repeats']}.",
        f"Source SHA-256: `{data['source_sha256']}`.",
        "",
        "See results.json for individual trials, operation mix, latency by operation, "
        "compiler flags, input hashes, and parity digests. These synthetic, single-process "
        "measurements do not represent network or production-exchange latency.",
    ]
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    (output / "throughput.png").unlink(missing_ok=True)
    if not chart:
        return
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(9, 4.6))
    for index, backend in enumerate(data["backends"]):
        values = [
            s["events_per_second"] / 1000 for w, b, s in summaries if b == backend
        ]
        ax.bar(
            [i + index * 0.36 for i in range(len(values))],
            values,
            yerr=[
                [
                    (s["events_per_second"] - s["min"]) / 1000
                    for w, b, s in summaries
                    if b == backend
                ],
                [
                    (s["max"] - s["events_per_second"]) / 1000
                    for w, b, s in summaries
                    if b == backend
                ],
            ],
            capsize=4,
            width=0.34,
            label=backend,
        )
    ax.set_xticks(
        [i + (len(data["backends"]) - 1) * 0.18 for i in range(len(data["workloads"]))],
        data["workloads"],
    )
    ax.set_ylabel("Thousand events / second (median)")
    ax.set_title(
        "Redline Exchange · API throughput (binding included; whiskers: trial range)"
    )
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(output / "throughput.png", dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--orders", type=int, default=20_000, help="events per workload"
    )
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument(
        "--workloads", nargs="+", choices=WORKLOADS, default=list(WORKLOADS)
    )
    parser.add_argument("--python-only", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("benchmark-results"))
    parser.add_argument(
        "--no-chart", action="store_true", help="save raw results without plotting"
    )
    args = parser.parse_args()
    if args.orders < 1 or args.repeats < 1:
        parser.error("orders and repeats must be positive")
    factories = {"python": LimitOrderBook}
    if not args.python_only:
        from orderbook.native import NativeLimitOrderBook

        factories["cpp"] = NativeLimitOrderBook
    data = dict(
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        count=args.orders,
        repeats=args.repeats,
        seed=args.seed,
        backends=list(factories),
        workloads=args.workloads,
        source_sha256=source_hash(),
        environment=dict(
            platform=platform.platform(),
            processor=platform.processor(),
            machine=platform.machine(),
            logical_cpus=os.cpu_count(),
            dependencies={
                p: importlib.metadata.version(p)
                for p in ["pybind11", "pytest", "hypothesis", "ruff", "matplotlib"]
                if importlib.util.find_spec(p)
            },
            python=platform.python_version(),
            gc_enabled=gc.isenabled(),
            clock=vars(time.get_clock_info("perf_counter")),
        ),
        inputs={},
        runs=[],
    )
    if "cpp" in factories:
        from orderbook import _native

        data["environment"]["native_compiler"] = _native.compiler
        data["environment"]["native_build"] = validate_native_build(
            ROOT, _native.__file__
        )
    for workload in args.workloads:
        events = generate(args.orders, args.seed, workload)
        data["inputs"][workload] = dict(
            sha256=workload_hash(events),
            operation_mix=dict(Counter(e[0] for e in events)),
            parity={
                name: verify(factory, events) for name, factory in factories.items()
            },
        )
        for factory in factories.values():
            replay(
                factory("BENCH", retain_trade_history=False),
                events[: min(2000, len(events))],
            )
        for trial in range(args.repeats):
            order = list(factories.items())
            if trial % 2:
                order.reverse()
            for name, factory in order:
                row = dict(
                    workload=workload,
                    backend=name,
                    trial=trial,
                    events=len(events),
                    **measure(factory, events),
                )
                data["runs"].append(row)
                print(
                    f"{workload} {name} trial {trial + 1}: {row['events_per_second']:,.0f} events/s",
                    flush=True,
                )
    report(data, args.output, chart=not args.no_chart)


if __name__ == "__main__":
    main()
