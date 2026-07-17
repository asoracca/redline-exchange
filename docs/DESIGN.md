# Redline Exchange design notes

## Why this project

The existing portfolio emphasizes analysis. This project demonstrates a different skill set: API design, state management, algorithms, correctness, testing, and performance measurement.

## Price representation

Prices are positive integer ticks. If one tick is one cent, `10100` represents 101.00. Integer ticks avoid binary floating-point equality and ordering problems.

## Data structures

- Bids: min-heap of negative prices, then arrival sequence.
- Asks: min-heap of positive prices, then arrival sequence.
- Active orders: dictionary keyed by order ID.

The heap key implements price priority and FIFO priority at equal prices. Cancellation removes the ID from the dictionary. Stale heap entries are removed lazily when they reach the top.

## Complexity

- Submit resting order: `O(log n)`.
- Best price lookup: amortized `O(log n)` with stale cleanup.
- Cancellation: `O(1)` dictionary removal.
- Match: `O(k log n)` for `k` fully consumed resting orders.
- Depth snapshot: `O(n)` because this educational implementation aggregates active orders on demand.

## Invariants

- active order IDs are unique;
- quantities and prices are positive integers;
- market orders never rest;
- every trade uses the resting order's price;
- filled and canceled orders do not appear in depth;
- price and time priority determine execution order.

## Honest limitations

- one process and one symbol per book;
- no persistence, networking, authentication, or concurrency;
- no stop, iceberg, pegged, IOC, or FOK orders;
- no modify operation;
- depth aggregation is not optimized;
- benchmark throughput is Python-specific and not exchange-grade latency.

## Next meaningful extensions

1. Add cancel/replace while preserving explicit priority rules.
2. Replay a CSV stream of add, cancel, and execute events.
3. Maintain price-level aggregates incrementally.
4. Publish p50/p95/p99 latency, not only average throughput.
5. Reimplement the core in C++ and compare identical event streams.
