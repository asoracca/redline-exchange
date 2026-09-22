# Redline Exchange design notes

## Why this project

The existing portfolio emphasizes analysis. This project demonstrates a different skill set: API design, state management, algorithms, correctness, testing, and performance measurement.

## Price representation

Prices are positive integer ticks. If one tick is one cent, `10100` represents 101.00. Integer ticks avoid binary floating-point equality and ordering problems.

## Data structures

- Bids: min-heap of negative prices, then arrival sequence.
- Asks: min-heap of positive prices, then arrival sequence.
- Active orders: dictionary keyed by order ID.

The heap key contains price, arrival sequence, and order ID. Cancellation removes
the ID from the dictionary. Replacement creates a new sequence when priority is
lost. Stale heap entries are removed lazily and are considered valid only when
their complete key matches the active order. This prevents an old heap entry
from accidentally referring to a replaced order with the same ID.

## Complexity

In heap operations below, `n` counts heap entries, including stale entries,
not just active orders. Hash-map operations are expected, not worst-case, O(1).

- Submit resting order: `O(log n)`.
- Best price lookup: amortized `O(log n)` with stale cleanup.
- Cancellation: `O(1)` dictionary removal.
- Same-price quantity reduction: `O(1)` and retains priority.
- Price change or quantity increase: `O(log n)` when the replacement rests.
- Match: `O(k log n)` for `k` fully consumed resting orders.
- Depth snapshot: `O(A + L log L)` for `A` active orders and `L` occupied price levels; aggregation is followed by sorting.

## Invariants

- active order IDs are unique;
- quantities and prices are positive integers;
- market orders never rest;
- every trade uses the resting order's price;
- filled and canceled orders do not appear in depth;
- price and time priority determine execution order.
- active orders have a matching price/sequence/ID heap entry;
- the book is not crossed after matching completes;
- trade sequences are strictly increasing;
- an order cannot trade more than its maximum accepted quantity.

## Honest limitations

- one process and one symbol per book;
- no persistence, networking, authentication, or concurrency;
- no stop, iceberg, pegged, IOC, or FOK orders;
- depth aggregation is not optimized;
- benchmark throughput is synthetic API throughput, not exchange-grade latency.
- seen IDs and accounting persist for the book lifetime; lazy heaps can retain canceled entries.
- replay is strict and single-symbol; it is not a durable event store.

## Optional native backend

The Python API and research code remain the default. The independent C++17 core
mirrors the heaps, ID map, replacement rules and invariant accounting. A small
pybind11 adapter returns the existing Python dataclasses. See [native design and
contract](NATIVE.md), [measured comparison](performance/SUMMARY.md), and
[profiling evidence](PROFILING.md).

## Next meaningful extensions

1. Benchmark incremental price-level aggregates for snapshot-heavy research.
2. Study periodic heap compaction against lazy cancellation under sustained churn.
3. Measure multiple seeds, larger counts and per-process memory separately.
4. Add a batched binding or standalone C++ runner with a separately labeled metric.
