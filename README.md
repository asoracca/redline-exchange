# Redline Exchange

A deterministic price-time-priority exchange matching engine implemented in
Python and C++20.

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
- cross-language differential tests that compare every trade and active order;
- reproducible throughput, p50, p95, and p99 latency benchmarks;
- AddressSanitizer and UndefinedBehaviorSanitizer checks in CI.

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

## C++20 engine

The C++ engine implements the same public matching semantics as Python rather
than a simplified benchmark-only loop. Build and verify it with:

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel
ctest --test-dir build --output-on-failure

REDLINE_CPP_BINARY="$PWD/build/redline_cpp" \
  python -m pytest tests/test_cpp_parity.py -q

python benchmark_cpp.py \
  --binary "$PWD/build/redline_cpp" \
  --orders 100000 \
  --output data/cpp_benchmark/comparison.csv
```

The parity fixture exercises limit and market orders, partial fills,
cancellation, priority-preserving reductions, and priority-losing replacement.
The test fails if either implementation disagrees on a trade field or the final
active-order state. See [the C++ design and methodology](docs/CPP_ENGINE.md)
and [the recorded results](docs/CPP_RESULTS.md).

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

## Market microstructure research

Redline Market Lab adds deterministic noise traders, informed traders, and an
inventory-aware market maker on top of the unchanged matching engine. It tests
how informed flow, quote latency, volatility, and inventory limits affect
marked P&L and risk.

```bash
python run_market_lab.py
python run_market_study.py
```

The second runner repeats five scenarios over 50 common random seeds, reports
approximate 95% confidence intervals, decomposes P&L into execution edge and
inventory revaluation, and creates a scenario chart. See
[the methodology](docs/MARKET_LAB.md) and [results](docs/RESULTS.md).

## Suggested development sequence

- Version 1: deterministic price-time engine and unit tests.
- Version 2: cancel/replace, CSV replay, invariants, property tests, and latency benchmarks.
- Version 3: agent-based market microstructure experiments and multi-seed inference.
- Version 4: C++ implementation, exact Python/C++ parity, sanitizer checks, and
  benchmark comparison.

Do not add a trading signal until the engine itself is correct, tested, and measured.
