"""Numerical evidence, independent of any language model."""

import csv
import hashlib
import io
import math
import platform
import statistics
import time
from pathlib import Path
from html import escape

from orderbook.market_lab import SimulationConfig, run_market_simulation
from .storage import digest


def provenance():
    root = Path(__file__).resolve().parents[1]
    files = {}
    for package in ("orderbook", "research_copilot"):
        for path in sorted((root / package).rglob("*.py")):
            files[str(path.relative_to(root))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    for path in sorted((root.parent / "cpp").glob("*")):
        if path.is_file():
            files["cpp/" + path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    for path in sorted((root / "orderbook").glob("*.so")):
        files[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(
        hash=digest(files),
        files=files,
        python=platform.python_version(),
        platform=platform.platform(),
        protocol=1,
    )


def execute(plan, scenario, seed_index):
    name = "baseline" if scenario == 0 else plan.treatments[scenario - 1].name
    params = (
        plan.baseline if scenario == 0 else plan.treatments[scenario - 1].parameters
    )
    seed = plan.seeds[seed_index] + (
        100000 * scenario if plan.kind == "simulation" else 0
    )
    if plan.kind == "simulation":
        result = run_market_simulation(
            SimulationConfig(steps=plan.steps, seed=seed, **params.model_dump())
        )
        metrics = result.summary()
        peak = drawdown = 0
        for record in result.records:
            peak = max(peak, record.marked_pnl_ticks)
            drawdown = max(drawdown, peak - record.marked_pnl_ticks)
        metrics["max_drawdown_ticks"] = drawdown
        metrics = {key: metrics[key] for key in plan.metrics}
        config = dict(
            steps=plan.steps,
            seed=seed,
            initial_fair_value_ticks=10000,
            **params.model_dump(),
        )
    else:
        from orderbook.book import LimitOrderBook
        from orderbook.native import NativeLimitOrderBook
        from orderbook.workloads import generate, verify, replay, workload_hash

        factory = LimitOrderBook if scenario == 0 else NativeLimitOrderBook
        events = generate(plan.steps, seed, plan.workload)
        parity = verify(factory, events)
        # Construction, generation and parity checks are outside the timed region.
        book = factory("BENCH", retain_trade_history=False)
        started = time.perf_counter_ns()
        replay(book, events)
        metrics = dict(
            core_api_ns_per_event=(time.perf_counter_ns() - started) / len(events)
        )
        config = dict(
            events=plan.steps,
            seed=seed,
            workload=plan.workload,
            workload_hash=workload_hash(events),
            parity_hash=parity,
            backend="python" if scenario == 0 else "cpp",
            retain_trade_history=False,
        )
    return dict(
        key=f"{scenario}:{seed_index}",
        scenario=name,
        scenario_index=scenario,
        seed=seed,
        config=config,
        metrics=metrics,
    )


def summarize(values):
    mean = statistics.mean(values)
    sd = statistics.stdev(values)
    half = 1.96 * sd / math.sqrt(len(values))
    return dict(n=len(values), mean=mean, sd=sd, low=mean - half, high=mean + half)


def compare(plan, rows):
    if len(rows) != (1 + len(plan.treatments)) * len(plan.seeds):
        raise ValueError("Incomplete evidence: every scheduled task is required")
    groups = {}
    for index in range(1 + len(plan.treatments)):
        selected = [r for r in rows if r["scenario_index"] == index]
        if len(selected) != len(plan.seeds) or len(
            {r["seed"] for r in selected}
        ) != len(plan.seeds):
            raise ValueError("Missing or duplicate seed evidence")
        groups[selected[0]["scenario"]] = {
            m: summarize([r["metrics"][m] for r in selected])
            for m in selected[0]["metrics"]
        }
    evidence = {}
    for name, metrics in groups.items():
        if name == "baseline":
            continue
        for metric, stats in metrics.items():
            baseline = groups["baseline"][metric]
            delta = stats["mean"] - baseline["mean"]
            half = 1.96 * math.sqrt(
                stats["sd"] ** 2 / stats["n"] + baseline["sd"] ** 2 / baseline["n"]
            )
            low, high = delta - half, delta + half
            conclusion = (
                "inconclusive"
                if stats["n"] < 5 or low <= 0 <= high
                else "positive"
                if low > 0
                else "negative"
            )
            eid = f"{name}.{metric}"
            evidence[eid] = dict(
                id=eid,
                treatment=name,
                metric=metric,
                delta=delta,
                low=low,
                high=high,
                n=stats["n"],
                conclusion=conclusion,
            )
    return dict(
        groups=groups,
        evidence=evidence,
        method="Unpaired difference of means; exploratory normal 95% intervals, 1.96 × standard error; sample SD (ddof=1). No multiplicity adjustment. n<5 is always inconclusive. No strong best-configuration ranking.",
        seed_schedule="Disjoint scenario offsets of 100000; no common-random-number claim."
        if plan.kind == "simulation"
        else "Identical prepared workloads by seed; conservative unpaired timing intervals; host noise and order effects remain.",
    )


def csv_results(rows):
    out = io.StringIO()
    fields = ["scenario", "seed"] + list(rows[0]["metrics"])
    writer = csv.DictWriter(out, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            dict(scenario=row["scenario"], seed=row["seed"], **row["metrics"])
        )
    return out.getvalue()


def chart(comparison):
    metric = next(iter(comparison["groups"]["baseline"]))
    groups = comparison["groups"]
    lo = min(0, *[g[metric]["low"] for g in groups.values()])
    hi = max(1, *[g[metric]["high"] for g in groups.values()])

    def scale(x):
        return 180 + 560 * (x - lo) / (hi - lo)

    height = 90 + len(groups) * 65
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 {height}" role="img" aria-label="Mean and exploratory 95 percent intervals"><rect width="800" height="{height}" fill="#101b26"/><text x="20" y="30" fill="#edf4f6" font-family="sans-serif" font-size="16">{escape(metric)} · mean and 95% interval</text>'
    ]
    for i, (name, values) in enumerate(groups.items()):
        s = values[metric]
        y = 75 + i * 65
        parts.append(
            f'<text x="20" y="{y + 5}" fill="#bacbd7" font-family="sans-serif" font-size="14">{escape(name)}</text><line x1="{scale(s["low"]):.2f}" x2="{scale(s["high"]):.2f}" y1="{y}" y2="{y}" stroke="#6de3ba" stroke-width="3"/><circle cx="{scale(s["mean"]):.2f}" cy="{y}" r="6" fill="#6de3ba"/><text x="{scale(s["mean"]):.2f}" y="{y + 25}" fill="#edf4f6" text-anchor="middle" font-family="sans-serif" font-size="12">{s["mean"]:.2f}</text>'
        )
    return "".join(parts) + "</svg>"


def render_report(plan, comparison, claims, review):
    evidence = comparison["evidence"]
    if {c.evidence_id for c in claims} != set(evidence) or len(claims) != len(evidence):
        raise ValueError("Report must reference every evidence ID exactly once")
    for claim in claims:
        if (
            claim.evidence_id not in evidence
            or claim.conclusion != evidence[claim.evidence_id]["conclusion"]
        ):
            raise ValueError("Unsupported claim or nonexistent evidence reference")
    lines = [
        "# Redline research report",
        "",
        "Synthetic simulation only. These results do not establish real-world trading performance.",
        "",
        f"Experiment: {plan.kind}. See [validated plan](plan.json) for the hypothesis and parameters.",
        "",
        "## Findings",
        "",
    ]
    for claim in claims:
        e = evidence[claim.evidence_id]
        lines.append(
            f"- **{e['treatment']} / {e['metric']}**: treatment minus baseline = **{e['delta']:.2f}**, exploratory 95% interval [{e['low']:.2f}, {e['high']:.2f}], n={e['n']} per group. Direction: **{e['conclusion']}**. [Evidence: {e['id']}](comparison.json)."
        )
    lines += [
        "",
        "## Method and limits",
        "",
        comparison["method"],
        comparison["seed_schedule"],
        "No causal mechanism or optimal strategy is asserted. P&L and edge are tick × quantity; inventory is quantity. Drawdown is the largest peak-to-trough marked P&L decline, including starting P&L zero. Quote refresh is measured in simulation steps, not network milliseconds.",
        "",
        f"Reviewer assessment: {review['assessment']}. Concerns: {', '.join(review['concerns'])}.",
        "",
        "[Seed results](results.csv) · [Chart inputs](chart-inputs.json) · [Chart](chart.svg) · [Action log](logs.json) · [Provenance and artifact hashes](evidence.json)",
    ]
    return "\n".join(lines) + "\n"


def validate_result(plan, scenario, seed_index, result):
    """Treat tool returns as data: reject extra instructions and mismatched evidence."""
    if set(result) != {
        "key",
        "scenario",
        "scenario_index",
        "seed",
        "config",
        "metrics",
    }:
        raise ValueError("Unexpected task result fields")
    expected_name = "baseline" if scenario == 0 else plan.treatments[scenario - 1].name
    expected_seed = plan.seeds[seed_index] + (
        100000 * scenario if plan.kind == "simulation" else 0
    )
    if (
        result["key"] != f"{scenario}:{seed_index}"
        or result["scenario_index"] != scenario
        or result["scenario"] != expected_name
        or result["seed"] != expected_seed
    ):
        raise ValueError("Task result does not match scheduled identity")
    expected_metrics = (
        set(plan.metrics) if plan.kind == "simulation" else {"core_api_ns_per_event"}
    )
    if set(result["metrics"]) != expected_metrics or any(
        type(v) not in (int, float) or not math.isfinite(v)
        for v in result["metrics"].values()
    ):
        raise ValueError("Task metrics invalid")
    if plan.kind == "simulation":
        parameters = (
            plan.baseline if scenario == 0 else plan.treatments[scenario - 1].parameters
        )
        expected = dict(
            steps=plan.steps,
            seed=expected_seed,
            initial_fair_value_ticks=10000,
            **parameters.model_dump(),
        )
        if result["config"] != expected:
            raise ValueError("Task parameters differ from validated plan")
    else:
        config = result["config"]
        expected = dict(
            events=plan.steps,
            seed=expected_seed,
            workload=plan.workload,
            backend="python" if scenario == 0 else "cpp",
            retain_trade_history=False,
        )
        if set(config) != set(expected) | {"workload_hash", "parity_hash"} or any(
            config[k] != v for k, v in expected.items()
        ):
            raise ValueError("Benchmark configuration differs from plan")
        if any(
            len(config[k]) != 64 or any(c not in "0123456789abcdef" for c in config[k])
            for k in ("workload_hash", "parity_hash")
        ):
            raise ValueError("Benchmark hashes invalid")
    return result
