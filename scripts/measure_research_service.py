"""Separate loopback HTTP, SQLite checkpoint, and end-to-end workflow samples.

Starts an isolated local server and temporary store. Never contacts a model.
"""

import argparse
import json
import math
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request

from research_copilot.experiments import provenance
from research_copilot.models import StartRequest
from research_copilot.planner import EXAMPLES
from research_copilot.storage import Store


def summary(samples):
    ordered = sorted(samples)
    return dict(
        n=len(samples),
        median_ms=statistics.median(samples),
        p95_ms=ordered[math.ceil(0.95 * len(samples)) - 1],
        samples_ms=samples,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("docs/research/service-timing-v2.json")
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = Store(root / "sqlite-only")
        try:
            run = store.create(
                StartRequest(question=EXAMPLES[0]).model_dump(), provenance()
            )
            sqlite_samples = []
            for i in range(200):
                start = time.perf_counter_ns()
                store.save_task(run["id"], str(i), {"probe": i}, f"probe-{i}")
                sqlite_samples.append((time.perf_counter_ns() - start) / 1e6)
        finally:
            store.close()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        env = dict(
            os.environ, REDLINE_RESEARCH_DIR=str(root / "http"), REDLINE_PUBLIC_DEMO="0"
        )
        env.pop("OPENAI_API_KEY", None)
        env.pop("OPENAI_MODEL", None)
        base = f"http://127.0.0.1:{port}"

        def get(path):
            with urllib.request.urlopen(base + path, timeout=5) as response:
                return json.load(response)

        with (root / "server.log").open("w") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "research_copilot.api:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                for _ in range(100):
                    try:
                        get("/healthz")
                        break
                    except OSError:
                        if process.poll() is not None:
                            raise RuntimeError("Timing server failed to start")
                        time.sleep(0.1)
                else:
                    raise RuntimeError("Timing server readiness timeout")
                http_samples = []
                for _ in range(20):
                    start = time.perf_counter_ns()
                    get("/api/research/runs")
                    http_samples.append((time.perf_counter_ns() - start) / 1e6)
                workflows = []
                for i in range(3):
                    start = time.perf_counter_ns()
                    request = urllib.request.Request(
                        base + "/api/research/runs",
                        data=json.dumps({"question": EXAMPLES[0]}).encode(),
                        headers={"Content-Type": "application/json"},
                    )
                    with urllib.request.urlopen(request, timeout=5) as response:
                        run = json.load(response)
                    deadline = time.monotonic() + 30
                    while time.monotonic() < deadline:
                        run = get("/api/research/runs/" + run["id"])
                        if run["state"] in {"completed", "failed"}:
                            break
                        time.sleep(0.02)
                    assert run["state"] == "completed", run["error"]
                    assert run["model_calls"] == 0
                    workflows.append(
                        dict(
                            trial=i,
                            elapsed_ms=(time.perf_counter_ns() - start) / 1e6,
                            worker_seconds=run["elapsed"],
                            cache_hits=sum(e["kind"] == "cache" for e in run["events"]),
                        )
                    )
            finally:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
    result = dict(
        command="python scripts/measure_research_service.py",
        source=provenance(),
        sqlite_checkpoint=summary(sqlite_samples),
        empty_history_loopback_http=summary(http_samples),
        quote_latency_workflows=workflows,
        notes=[
            "SQLite: 200 tiny task+cache transactions, WAL synchronous=FULL; serialization and local filesystem included, no simulator.",
            "HTTP: 20 empty-history GETs against one warmed local Uvicorn process; includes HTTP/SQLite, no matching. No load/concurrency claim.",
            "Workflow: three sequential identical scripted studies; first cold, later cached as shown. Includes HTTP and 20ms completion polling, not browser render.",
            "Core API and browser samples are separate artifacts. Do not subtract these unlike workloads to estimate overhead. No external model calls.",
        ],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in {"source", "notes"}}, indent=2
        )
    )


if __name__ == "__main__":
    main()
