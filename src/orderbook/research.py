from __future__ import annotations

import csv
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace
from pathlib import Path

from .market_lab import SimulationConfig, run_market_simulation


def mean_confidence_interval(values: Sequence[float]) -> tuple[float, float, float]:
    """Return the sample mean and a normal-approximation 95% interval."""
    if len(values) < 2:
        raise ValueError("at least two observations are required")
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    standard_error = math.sqrt(variance / len(values))
    margin = 1.96 * standard_error
    return mean, mean - margin, mean + margin


def run_scenario_study(
    scenarios: Mapping[str, SimulationConfig], seeds: Iterable[int]
) -> tuple[list[dict[str, float | int | str]], list[dict[str, float | int | str]]]:
    """Run each scenario over common seeds and aggregate key measurements."""
    seed_list = list(seeds)
    if len(seed_list) < 2:
        raise ValueError("at least two seeds are required")

    runs: list[dict[str, float | int | str]] = []
    for scenario, config in scenarios.items():
        for seed in seed_list:
            summary = run_market_simulation(replace(config, seed=seed)).summary()
            runs.append({"scenario": scenario, "seed": seed, **summary})

    aggregated: list[dict[str, float | int | str]] = []
    for scenario in scenarios:
        selected = [row for row in runs if row["scenario"] == scenario]
        pnl = [float(row["ending_pnl_ticks"]) for row in selected]
        inventory = [float(row["max_abs_inventory"]) for row in selected]
        edge = [float(row["maker_edge_ticks_per_unit"]) for row in selected]
        pnl_mean, pnl_low, pnl_high = mean_confidence_interval(pnl)
        inventory_mean, _, _ = mean_confidence_interval(inventory)
        edge_mean, _, _ = mean_confidence_interval(edge)
        aggregated.append(
            {
                "scenario": scenario,
                "runs": len(selected),
                "mean_ending_pnl_ticks": pnl_mean,
                "pnl_ci95_low": pnl_low,
                "pnl_ci95_high": pnl_high,
                "mean_max_abs_inventory": inventory_mean,
                "mean_edge_ticks_per_unit": edge_mean,
            }
        )
    return runs, aggregated


def write_dict_rows(path: str | Path, rows: Sequence[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("rows cannot be empty")
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
