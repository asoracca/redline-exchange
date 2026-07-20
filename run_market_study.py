from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt

from orderbook.market_lab import SimulationConfig
from orderbook.research import run_scenario_study, write_dict_rows


def main() -> None:
    output = Path("data/market_study")
    base = SimulationConfig(steps=2_000)
    scenarios = {
        "baseline": base,
        "more informed": replace(base, informed_share=0.60),
        "slow quotes": replace(base, quote_refresh_interval=5),
        "higher volatility": replace(base, volatility_ticks=8),
        "tight inventory": replace(base, max_inventory=30),
    }
    runs, summary = run_scenario_study(scenarios, seeds=range(50))
    write_dict_rows(output / "all_runs.csv", runs)
    write_dict_rows(output / "summary.csv", summary)

    names = [str(row["scenario"]) for row in summary]
    means = [float(row["mean_ending_pnl_ticks"]) for row in summary]
    lower_errors = [
        means[index] - float(row["pnl_ci95_low"]) for index, row in enumerate(summary)
    ]
    upper_errors = [
        float(row["pnl_ci95_high"]) - means[index] for index, row in enumerate(summary)
    ]
    figure, axis = plt.subplots(figsize=(10, 5.5))
    axis.bar(
        names,
        means,
        yerr=[lower_errors, upper_errors],
        capsize=5,
        color="#d9472b",
    )
    axis.axhline(0, color="black", linewidth=0.8)
    axis.set_title("Redline Market Lab: mean ending P&L across 50 seeds")
    axis.set_ylabel("Marked P&L (tick-quantity units)")
    axis.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    output.mkdir(parents=True, exist_ok=True)
    figure.savefig(output / "pnl_by_scenario.png", dpi=180)
    plt.close(figure)

    print("REDLINE MULTI-SEED STUDY")
    for row in summary:
        print(
            f"{row['scenario']:<20} "
            f"mean={row['mean_ending_pnl_ticks']:>10.1f} "
            f"95% CI=[{row['pnl_ci95_low']:>10.1f}, "
            f"{row['pnl_ci95_high']:>10.1f}]"
        )
    print(f"\nSaved study outputs to {output}/")


if __name__ == "__main__":
    main()
