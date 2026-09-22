"""Repeat the existing API comparison across seeds in fresh Python processes."""

import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import sys

from orderbook.workloads import WORKLOADS

ROOT = Path(__file__).resolve().parent


def summarize(datasets):
    if not datasets:
        raise ValueError("at least one result required")
    first = datasets[0]
    fields = (
        "count",
        "repeats",
        "workloads",
        "backends",
        "source_sha256",
        "environment",
    )
    if any(any(d[field] != first[field] for field in fields) for d in datasets):
        raise ValueError("cannot combine different protocols, sources or environments")
    if len({d["seed"] for d in datasets}) != len(datasets):
        raise ValueError("duplicate seeds do not establish input diversity")
    rows = []
    for data in datasets:
        for workload in data["workloads"]:
            medians = {}
            for backend in data["backends"]:
                runs = [
                    r
                    for r in data["runs"]
                    if r["workload"] == workload and r["backend"] == backend
                ]
                if len(runs) != data["repeats"] or {r["trial"] for r in runs} != set(
                    range(data["repeats"])
                ):
                    raise ValueError("incomplete or duplicate trials")
                medians[backend] = statistics.median(
                    r["events_per_second"] for r in runs
                )
            rows.append(
                dict(
                    seed=data["seed"],
                    workload=workload,
                    python_events_per_second=medians["python"],
                    cpp_events_per_second=medians["cpp"],
                    speedup=medians["cpp"] / medians["python"],
                )
            )
    return dict(
        seeds=[d["seed"] for d in datasets],
        count=first["count"],
        repeats=first["repeats"],
        source_sha256=first["source_sha256"],
        rows=rows,
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--orders", type=int, default=100_000)
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--seeds", type=int, nargs="+", default=[17, 42, 73])
    p.add_argument("--workloads", nargs="+", choices=WORKLOADS, default=list(WORKLOADS))
    p.add_argument("--output", type=Path, default=Path("benchmark-results"))
    args = p.parse_args()
    if args.orders < 1 or args.repeats < 1 or len(set(args.seeds)) != len(args.seeds):
        p.error("positive orders/repeats and distinct seeds required")
    output = args.output.resolve()
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    datasets = []
    for index, seed in enumerate(args.seeds):
        destination = output if index == 0 else output / f"seed-{seed}"
        command = [
            sys.executable,
            str(ROOT / "compare.py"),
            "--orders",
            str(args.orders),
            "--repeats",
            str(args.repeats),
            "--seed",
            str(seed),
            "--workloads",
            *args.workloads,
            "--output",
            str(destination),
        ]
        if index:
            command.append("--no-chart")
        subprocess.run(command, env=env, cwd=ROOT, check=True)
        datasets.append(json.loads((destination / "results.json").read_text()))
    result = summarize(datasets)
    (output / "study.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# Comparison across seeds",
        "",
        f"{args.orders:,} events per workload; {args.repeats} trials per backend and seed.",
        "Each seed runs in a fresh process; matching rules and API timing are unchanged.",
        "",
        "| Seed | Workload | Python events/s | C++ events/s | Ratio of medians |",
        "|---:|---|---:|---:|---:|",
    ]
    for r in result["rows"]:
        lines.append(
            f"| {r['seed']} | {r['workload']} | {r['python_events_per_second']:,.0f} | "
            f"{r['cpp_events_per_second']:,.0f} | {r['speedup']:.2f}× |"
        )
    lines += [
        "",
        "These are input-seed checks on one host, not confidence intervals across hardware.",
        "The cancel/replace stream is deliberately identical across seeds; its repeats test",
        "run variability, not input diversity. No trial is dropped.",
        "",
        "The first seed uses [results.json](results.json) and [SUMMARY.md](SUMMARY.md).",
    ]
    for seed in args.seeds[1:]:
        lines.append(
            f"- Seed {seed}: [raw trials](seed-{seed}/results.json) · [table](seed-{seed}/SUMMARY.md)"
        )
    lines += ["", f"Source SHA-256: `{result['source_sha256']}`."]
    (output / "STUDY.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
