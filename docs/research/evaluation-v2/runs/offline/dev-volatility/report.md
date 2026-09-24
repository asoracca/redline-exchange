# Redline research report

Synthetic simulation only. These results do not establish real-world trading performance.

Experiment: simulation. See [validated plan](plan.json) for the hypothesis and parameters.

## Findings

- **volatile / ending_pnl_ticks**: treatment minus baseline = **-1213.33**, exploratory 95% interval [-9323.71, 6897.04], n=6 per group. Direction: **inconclusive**. [Evidence: volatile.ending_pnl_ticks](comparison.json).
- **volatile / execution_edge_pnl_ticks**: treatment minus baseline = **-2240.00**, exploratory 95% interval [-3068.02, -1411.98], n=6 per group. Direction: **negative**. [Evidence: volatile.execution_edge_pnl_ticks](comparison.json).
- **volatile / inventory_revaluation_pnl_ticks**: treatment minus baseline = **1026.67**, exploratory 95% interval [-6922.98, 8976.31], n=6 per group. Direction: **inconclusive**. [Evidence: volatile.inventory_revaluation_pnl_ticks](comparison.json).
- **volatile / max_abs_inventory**: treatment minus baseline = **1.67**, exploratory 95% interval [-1.60, 4.93], n=6 per group. Direction: **inconclusive**. [Evidence: volatile.max_abs_inventory](comparison.json).
- **volatile / max_drawdown_ticks**: treatment minus baseline = **5276.67**, exploratory 95% interval [183.95, 10369.38], n=6 per group. Direction: **positive**. [Evidence: volatile.max_drawdown_ticks](comparison.json).

## Method and limits

Unpaired difference of means; exploratory normal 95% intervals, 1.96 × standard error; sample SD (ddof=1). No multiplicity adjustment. n<5 is always inconclusive. No strong best-configuration ranking.
Disjoint scenario offsets of 100000; no common-random-number claim.
No causal mechanism or optimal strategy is asserted. P&L and edge are tick × quantity; inventory is quantity. Drawdown is the largest peak-to-trough marked P&L decline, including starting P&L zero. Quote refresh is measured in simulation steps, not network milliseconds.

Reviewer assessment: inconclusive. Concerns: synthetic_only, uncertain_difference, multiple_comparisons.

[Seed results](results.csv) · [Chart inputs](chart-inputs.json) · [Chart](chart.svg) · [Action log](logs.json) · [Provenance and artifact hashes](evidence.json)
