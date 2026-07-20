# Redline Market Lab

## Research question

How do informed order flow, quote-refresh latency, volatility, and inventory
limits affect a simple market maker's profit and risk?

## Design

The experiment wraps the existing price-time-priority matching engine without
changing its rules. A latent fundamental price follows a bounded discrete
random walk. At each step either a noise trader submits a randomly directed
market order or an informed trader trades only when the stale best quote is
mispriced relative to the new fundamental value.

An inventory-aware market maker cancels and replaces a bid and ask around an
inventory-skewed reservation price. Quote-refresh intervals greater than one
create controlled latency. Every experiment is seeded and deterministic.

## Reported measurements

- marked-to-fundamental ending P&L;
- maximum absolute inventory;
- average quoted spread;
- fills and traded volume;
- informed share of executed volume;
- maker edge at execution relative to fundamental value.

## Scenarios

`run_market_lab.py` compares a baseline with more informed flow, slower quote
refreshes, higher fundamental volatility, and a tighter inventory constraint.
The output is saved under `data/market_lab/` for analysis.

## Interpretation limits

This is a controlled agent-based experiment, not evidence that a strategy is
profitable in a real market. The order flow, fundamental process, latency, and
agents are synthetic. There are no exchange fees, queue-position uncertainty,
hidden liquidity, or calibrated arrival processes. Results should be treated
as mechanisms to inspect and hypotheses to refine, not trading claims.
