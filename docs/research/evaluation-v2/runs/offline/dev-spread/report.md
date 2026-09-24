# Redline research report

Synthetic simulation only. These results do not establish real-world trading performance.

Experiment: simulation. See [validated plan](plan.json) for the hypothesis and parameters.

## Findings

- **wide_spread / ending_pnl_ticks**: treatment minus baseline = **12521.67**, exploratory 95% interval [9529.88, 15513.46], n=6 per group. Direction: **positive**. [Evidence: wide_spread.ending_pnl_ticks](comparison.json).
- **wide_spread / execution_edge_pnl_ticks**: treatment minus baseline = **11398.33**, exploratory 95% interval [10874.67, 11922.00], n=6 per group. Direction: **positive**. [Evidence: wide_spread.execution_edge_pnl_ticks](comparison.json).
- **wide_spread / inventory_revaluation_pnl_ticks**: treatment minus baseline = **1123.33**, exploratory 95% interval [-2268.65, 4515.32], n=6 per group. Direction: **inconclusive**. [Evidence: wide_spread.inventory_revaluation_pnl_ticks](comparison.json).
- **wide_spread / max_abs_inventory**: treatment minus baseline = **1.67**, exploratory 95% interval [-1.60, 4.93], n=6 per group. Direction: **inconclusive**. [Evidence: wide_spread.max_abs_inventory](comparison.json).
- **wide_spread / max_drawdown_ticks**: treatment minus baseline = **-196.67**, exploratory 95% interval [-907.47, 514.13], n=6 per group. Direction: **inconclusive**. [Evidence: wide_spread.max_drawdown_ticks](comparison.json).

## Method and limits

Unpaired difference of means; exploratory normal 95% intervals, 1.96 × standard error; sample SD (ddof=1). No multiplicity adjustment. n<5 is always inconclusive. No strong best-configuration ranking.
Disjoint scenario offsets of 100000; no common-random-number claim.
No causal mechanism or optimal strategy is asserted. P&L and edge are tick × quantity; inventory is quantity. Drawdown is the largest peak-to-trough marked P&L decline, including starting P&L zero. Quote refresh is measured in simulation steps, not network milliseconds.

Reviewer assessment: inconclusive. Concerns: synthetic_only, uncertain_difference, multiple_comparisons.

[Seed results](results.csv) · [Chart inputs](chart-inputs.json) · [Chart](chart.svg) · [Action log](logs.json) · [Provenance and artifact hashes](evidence.json)
