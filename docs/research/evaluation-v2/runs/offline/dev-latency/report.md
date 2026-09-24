# Redline research report

Synthetic simulation only. These results do not establish real-world trading performance.

Experiment: simulation. See [validated plan](plan.json) for the hypothesis and parameters.

## Findings

- **slow_quotes / ending_pnl_ticks**: treatment minus baseline = **-3186.67**, exploratory 95% interval [-5565.69, -807.65], n=6 per group. Direction: **negative**. [Evidence: slow_quotes.ending_pnl_ticks](comparison.json).
- **slow_quotes / execution_edge_pnl_ticks**: treatment minus baseline = **-4493.33**, exploratory 95% interval [-4913.97, -4072.70], n=6 per group. Direction: **negative**. [Evidence: slow_quotes.execution_edge_pnl_ticks](comparison.json).
- **slow_quotes / inventory_revaluation_pnl_ticks**: treatment minus baseline = **1306.67**, exploratory 95% interval [-1250.76, 3864.10], n=6 per group. Direction: **inconclusive**. [Evidence: slow_quotes.inventory_revaluation_pnl_ticks](comparison.json).
- **slow_quotes / max_abs_inventory**: treatment minus baseline = **-56.67**, exploratory 95% interval [-66.57, -46.76], n=6 per group. Direction: **negative**. [Evidence: slow_quotes.max_abs_inventory](comparison.json).
- **slow_quotes / max_drawdown_ticks**: treatment minus baseline = **-1005.00**, exploratory 95% interval [-1595.34, -414.66], n=6 per group. Direction: **negative**. [Evidence: slow_quotes.max_drawdown_ticks](comparison.json).

## Method and limits

Unpaired difference of means; exploratory normal 95% intervals, 1.96 × standard error; sample SD (ddof=1). No multiplicity adjustment. n<5 is always inconclusive. No strong best-configuration ranking.
Disjoint scenario offsets of 100000; no common-random-number claim.
No causal mechanism or optimal strategy is asserted. P&L and edge are tick × quantity; inventory is quantity. Drawdown is the largest peak-to-trough marked P&L decline, including starting P&L zero. Quote refresh is measured in simulation steps, not network milliseconds.

Reviewer assessment: inconclusive. Concerns: synthetic_only, uncertain_difference, multiple_comparisons.

[Seed results](results.csv) · [Chart inputs](chart-inputs.json) · [Chart](chart.svg) · [Action log](logs.json) · [Provenance and artifact hashes](evidence.json)
