# C++ engine design and validation

## Research question

How much throughput can a compiled implementation gain without changing the
matching rules or weakening correctness checks?

That wording matters. Comparing unrelated engines would confound language,
data structures, and behavior. Redline instead runs one deterministic event
trace through two implementations of the same specification.

## Data structures

The C++20 engine stores:

- active orders in an `unordered_map` keyed by order ID;
- bids in a descending `std::map` of price levels;
- asks in an ascending `std::map` of price levels;
- each price level as a FIFO `deque` of `(order_id, sequence)` references.

Cancellation is lazy: the active-order map is authoritative and stale queue
references are discarded when they reach the front. A reference contains both
the ID and sequence, so an old reference cannot become live again after an
order is replaced under the same ID.

## Matching and replacement semantics

Both implementations enforce:

1. price priority before time priority;
2. execution at the resting order's price;
3. partial fills across price levels;
4. no resting remainder for market orders;
5. same-price quantity reduction retains priority;
6. quantity increases and repricing lose priority;
7. a replacement may execute immediately.

Prices use signed 64-bit integer ticks and quantities use unsigned 64-bit
integers. Floating-point money never enters the book.

## Validation layers

The upgrade deliberately uses several different kinds of evidence:

- native C++ unit tests target matching and replacement edge cases;
- Python property tests continue to generate randomized event sequences;
- differential replay compares every trade field and every surviving order;
- C++ invariants reject crossed books, invalid quantities, duplicate IDs, and
  inconsistent execution totals;
- GitHub Actions builds a release binary and a second debug binary with
  AddressSanitizer and UndefinedBehaviorSanitizer.

Passing a benchmark is not evidence of matching correctness. Passing parity on
one fixture is also not a proof for all possible inputs, so the fixture and
native tests are kept small, readable, and complementary to property testing.

## Benchmark methodology

`benchmark_cpp.py` creates one seeded CSV stream of limit orders. Python and
C++ consume that exact file. The runner verifies equal event, trade, and active
order counts before reporting performance.

End-to-end throughput times the replay loop. Per-event percentiles time the
matching call. CSV generation, process startup, output serialization, and final
invariant scans are excluded. The C++ target is compiled in release mode.

This is an implementation benchmark, not a claim about production-exchange
capacity. It omits networking, persistence, concurrency, risk controls,
recovery, market-data fanout, and kernel-bypass I/O.

## Reproduce

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
