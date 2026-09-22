"""Separate core-call and durable-service timing; deterministic resting workload."""

import argparse
import json
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path
from importlib.metadata import version

from exchange.schemas import Limit
from exchange.service import Exchange
from orderbook import LimitOrderBook, Side
from orderbook.native import NativeLimitOrderBook


def summarize(values):
    ordered = sorted(values)
    return {
        "samples": len(values),
        "p50_us": statistics.median(values) / 1000,
        "p95_us": ordered[round((len(values) - 1) * 0.95)] / 1000,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=200)
    parser.add_argument("--output", type=Path, default=Path("docs/service-timing.json"))
    args = parser.parse_args()
    if not 1 <= args.events <= 2000:
        parser.error("events must be 1..2000")
    result = dict(
        python=sys.version,
        platform=platform.platform(),
        dependencies={p: version(p) for p in ["fastapi", "pydantic", "uvicorn"]},
        workload="No RNG: i=0..N-1; BUY 1 at 10000+i ticks, unique IDs",
        units="microseconds",
        results={},
    )
    for name, factory in [("python", LimitOrderBook), ("cpp", NativeLimitOrderBook)]:
        core = factory("DEMO")
        core_times = []
        for i in range(args.events):
            start = time.perf_counter_ns()
            core.submit_limit(str(i), Side.BUY, 1, 10000 + i)
            core_times.append(time.perf_counter_ns() - start)
        with tempfile.TemporaryDirectory() as directory:
            service = Exchange(str(Path(directory) / "timing.sqlite3"), name)
            service_times = []
            for i in range(args.events):
                command = Limit(
                    kind="LIMIT",
                    request_id=str(i),
                    symbol="DEMO",
                    order_id=str(i),
                    side="BUY",
                    quantity=1,
                    price_ticks=10000 + i,
                )
                start = time.perf_counter_ns()
                service.submit(command)
                service_times.append(time.perf_counter_ns() - start)
            service.replay()
            service.close()
        result["results"][name] = {
            "core_api": summarize(core_times),
            "service_with_sqlite": summarize(service_times),
        }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
