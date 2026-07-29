from __future__ import annotations

import csv
from dataclasses import replace
from pathlib import Path

from orderbook.market_lab import SimulationConfig, run_market_simulation


def main() -> None:
    output = Path("data/market_lab")
    output.mkdir(parents=True, exist_ok=True)
    baseline = SimulationConfig(steps=5_000, seed=17)
    scenarios = {
        "baseline": baseline,
        "more_informed": replace(baseline, informed_share=0.60),
        "slow_quotes": replace(baseline, quote_refresh_interval=5),
        "higher_volatility": replace(baseline, volatility_ticks=8),
        "tight_inventory": replace(baseline, max_inventory=30),
    }

    rows: list[dict[str, object]] = []
    for name, config in scenarios.items():
        result = run_market_simulation(config)
        rows.append({"scenario": name, **result.summary()})
        if name == "baseline":
            result.write_records_csv(output / "baseline_path.csv")

    results_path = output / "scenario_results.csv"
    with results_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    headings = list(rows[0])
    widths = {
        heading: max(len(heading), *(len(f"{row[heading]}") for row in rows))
        for heading in headings
    }
    print("REDLINE MARKET LAB")
    print("  ".join(heading.ljust(widths[heading]) for heading in headings))
    for row in rows:
        print(
            "  ".join(f"{row[heading]}".ljust(widths[heading]) for heading in headings)
        )
    print(f"\nSaved results to {output}/")


if __name__ == "__main__":
    main()
