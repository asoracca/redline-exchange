# Redline research report

Synthetic simulation only. These results do not establish real-world trading performance.

Experiment: simulation. See [validated plan](plan.json) for the hypothesis and parameters.

## Findings

- **tight_inventory / ending_pnl_ticks**: treatment minus baseline = **126.67**, exploratory 95% interval [-942.72, 1196.06], n=6 per group. Direction: **inconclusive**. [Evidence: tight_inventory.ending_pnl_ticks](comparison.json).
- **tight_inventory / execution_edge_pnl_ticks**: treatment minus baseline = **-1020.00**, exploratory 95% interval [-1370.72, -669.28], n=6 per group. Direction: **negative**. [Evidence: tight_inventory.execution_edge_pnl_ticks](comparison.json).
- **tight_inventory / inventory_revaluation_pnl_ticks**: treatment minus baseline = **1146.67**, exploratory 95% interval [32.13, 2261.21], n=6 per group. Direction: **positive**. [Evidence: tight_inventory.inventory_revaluation_pnl_ticks](comparison.json).
- **tight_inventory / max_abs_inventory**: treatment minus baseline = **-35.00**, exploratory 95% interval [-43.39, -26.61], n=6 per group. Direction: **negative**. [Evidence: tight_inventory.max_abs_inventory](comparison.json).
- **tight_inventory / max_drawdown_ticks**: treatment minus baseline = **-468.33**, exploratory 95% interval [-721.39, -215.28], n=6 per group. Direction: **negative**. [Evidence: tight_inventory.max_drawdown_ticks](comparison.json).

## Method and limits

Unpaired difference of means; exploratory normal 95% intervals, 1.96 × standard error; sample SD (ddof=1). No multiplicity adjustment. n<5 is always inconclusive. No strong best-configuration ranking.
Disjoint scenario offsets of 100000; no common-random-number claim.
No causal mechanism or optimal strategy is asserted. P&L and edge are tick × quantity; inventory is quantity. Drawdown is the largest peak-to-trough marked P&L decline, including starting P&L zero. Quote refresh is measured in simulation steps, not network milliseconds.

Reviewer assessment: inconclusive. Concerns: synthetic_only, uncertain_difference, multiple_comparisons.

[Seed results](results.csv) · [Chart inputs](chart-inputs.json) · [Chart](chart.svg) · [Action log](logs.json) · [Provenance and artifact hashes](evidence.json)
