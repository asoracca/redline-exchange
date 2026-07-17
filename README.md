# Redline Exchange

A deterministic price-time-priority exchange matching engine written in Python.

This is a software-engineering project, not a trading-strategy dashboard. It focuses on data structures, deterministic behavior, invariants, and performance.

## Features

- limit and market orders;
- buy and sell sides;
- price-time priority;
- partial fills across multiple price levels;
- cancellation by order ID;
- resting-order (maker) execution prices;
- top-of-book and depth snapshots;
- integer price ticks to avoid floating-point money errors;
- unit tests and a reproducible benchmark.

## Quickstart

```bash
git clone https://github.com/asoracca/redline-exchange.git
cd redline-exchange
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .

python -m unittest discover -s tests -v
python -m orderbook.cli
redline-demo
python benchmark.py --orders 100000
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

See [docs/DESIGN.md](docs/DESIGN.md) for the data structures, complexity, and extension plan.

## Suggested development sequence

- Version 1: current deterministic engine and tests.
- Version 2: modify-order support and order-event replay from CSV.
- Version 3: WebSocket feed and a small depth visualization.
- Version 4: C++ implementation and Python/C++ benchmark comparison.

Do not add a trading signal until the engine itself is correct, tested, and measured.
