# Redline research report

Synthetic simulation only. These results do not establish real-world trading performance.

Experiment: simulation. See [validated plan](plan.json) for the hypothesis and parameters.

## Findings

- **tight_inventory / ending_pnl_ticks**: treatment minus baseline = **-1125.00**, exploratory 95% interval [-3372.11, 1122.11], n=6 per group. Direction: **inconclusive**. [Evidence: tight_inventory.ending_pnl_ticks](comparison.json).
- **tight_inventory / execution_edge_pnl_ticks**: treatment minus baseline = **-1653.33**, exploratory 95% interval [-1991.59, -1315.07], n=6 per group. Direction: **negative**. [Evidence: tight_inventory.execution_edge_pnl_ticks](comparison.json).
- **tight_inventory / inventory_revaluation_pnl_ticks**: treatment minus baseline = **528.33**, exploratory 95% interval [-1922.83, 2979.50], n=6 per group. Direction: **inconclusive**. [Evidence: tight_inventory.inventory_revaluation_pnl_ticks](comparison.json).
- **tight_inventory / max_abs_inventory**: treatment minus baseline = **-78.33**, exploratory 95% interval [-81.60, -75.07], n=6 per group. Direction: **negative**. [Evidence: tight_inventory.max_abs_inventory](comparison.json).
- **tight_inventory / max_drawdown_ticks**: treatment minus baseline = **-1361.67**, exploratory 95% interval [-1851.78, -871.55], n=6 per group. Direction: **negative**. [Evidence: tight_inventory.max_drawdown_ticks](comparison.json).
- **wide_spread / ending_pnl_ticks**: treatment minus baseline = **12745.00**, exploratory 95% interval [10001.53, 15488.47], n=6 per group. Direction: **positive**. [Evidence: wide_spread.ending_pnl_ticks](comparison.json).
- **wide_spread / execution_edge_pnl_ticks**: treatment minus baseline = **11918.33**, exploratory 95% interval [11037.01, 12799.66], n=6 per group. Direction: **positive**. [Evidence: wide_spread.execution_edge_pnl_ticks](comparison.json).
- **wide_spread / inventory_revaluation_pnl_ticks**: treatment minus baseline = **826.67**, exploratory 95% interval [-2095.03, 3748.37], n=6 per group. Direction: **inconclusive**. [Evidence: wide_spread.inventory_revaluation_pnl_ticks](comparison.json).
- **wide_spread / max_abs_inventory**: treatment minus baseline = **1.67**, exploratory 95% interval [-1.60, 4.93], n=6 per group. Direction: **inconclusive**. [Evidence: wide_spread.max_abs_inventory](comparison.json).
- **wide_spread / max_drawdown_ticks**: treatment minus baseline = **-91.67**, exploratory 95% interval [-865.25, 681.92], n=6 per group. Direction: **inconclusive**. [Evidence: wide_spread.max_drawdown_ticks](comparison.json).

## Method and limits

Unpaired difference of means; exploratory normal 95% intervals, 1.96 × standard error; sample SD (ddof=1). No multiplicity adjustment. n<5 is always inconclusive. No strong best-configuration ranking.
Disjoint scenario offsets of 100000; no common-random-number claim.
No causal mechanism or optimal strategy is asserted. P&L and edge are tick × quantity; inventory is quantity. Drawdown is the largest peak-to-trough marked P&L decline, including starting P&L zero. Quote refresh is measured in simulation steps, not network milliseconds.

Reviewer assessment: inconclusive. Concerns: synthetic_only, uncertain_difference, multiple_comparisons.

[Seed results](results.csv) · [Chart inputs](chart-inputs.json) · [Chart](chart.svg) · [Action log](logs.json) · [Provenance and artifact hashes](evidence.json)
