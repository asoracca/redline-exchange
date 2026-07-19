# Redline Exchange

A deterministic price-time-priority exchange matching engine written in Python.

This is a software-engineering project, not a trading-strategy dashboard. It focuses on data structures, deterministic behavior, invariants, and performance.

## Features

- limit and market orders;
- buy and sell sides;
- price-time priority;
- partial fills across multiple price levels;
- cancellation by order ID;
- cancel/replace with explicit queue-priority rules;
- deterministic CSV event replay;
- resting-order (maker) execution prices;
- top-of-book and depth snapshots;
- integer price ticks to avoid floating-point money errors;
- invariant and property-based tests;
- reproducible throughput, p50, and p95 latency benchmarks.

## Quickstart

```bash
git clone https://github.com/asoracca/redline-exchange.git
cd redline-exchange
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"

python -m pytest -q
python -m orderbook.cli
redline-demo
redline-replay examples/events.csv --symbol DEMO
python benchmark.py --orders 10000 100000 1000000 --csv benchmark-results.csv
```

On Windows PowerShell, activate the environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## Example

```python
from orderbook import LimitOrderBook, Side

book = LimitOrderBook(symbol="DEMO")
book.submit_limit("sell-1", Side.SELL, quantity=100, price_ticks=10100)
trades = book.submit_limit("buy-1", Side.BUY, quantity=40, price_ticks=10100)

print(trades[0])
print(book.top_of_book())
```

`10100` means 101.00 when the tick size is one cent. The engine stores integer ticks internally.

## Matching rules

1. Better prices execute first.
2. At the same price, earlier orders execute first.
3. A trade executes at the resting order's price.
4. Unfilled limit quantity rests on the book.
5. Unfilled market quantity is canceled rather than resting.

## Replace rules

`replace(order_id, new_quantity, new_price_ticks=None)` treats quantity as the
new **remaining** quantity.

- Reducing quantity at the same price keeps the original sequence and priority.
- Increasing quantity loses priority.
- Changing price loses priority and may immediately trade.
- Zero quantity is rejected; use `cancel` instead.

Heap entries include price, sequence, and order ID. A stale entry from a cancel
or replacement cannot be mistaken for the active version of an order.

## Correctness checks

`assert_invariants()` verifies that active orders have valid heap entries, the
book is not crossed after matching, trade sequences increase, quantities remain
positive, and no order trades more than its maximum accepted quantity.

The Hypothesis test suite generates randomized submissions, markets, cancels,
and replacements and checks these invariants after every event.

See [event replay](docs/REPLAY.md) and [benchmark methodology](docs/BENCHMARKS.md).

See [docs/DESIGN.md](docs/DESIGN.md) for the data structures, complexity, and extension plan.

## Suggested development sequence

- Version 1: deterministic price-time engine and unit tests.
- Version 2: cancel/replace, CSV replay, invariants, property tests, and latency benchmarks.
- Version 3: incremental price-level aggregates and a small depth visualization.
- Version 4: C++ implementation and Python/C++ benchmark comparison.

Do not add a trading signal until the engine itself is correct, tested, and measured.
