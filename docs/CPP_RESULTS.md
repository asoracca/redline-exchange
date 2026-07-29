# Python versus C++ results

## Correctness result

The native C++ unit suite passes, and differential replay produces the same:

- trade sequence;
- symbol and integer execution price;
- execution quantity;
- maker and taker IDs;
- taker side;
- final active-order quantities and queue sequences.

The complete Python suite, including randomized property tests and the new
parity test, passes with 32 tests.

## Performance snapshot

Recorded on 2026-07-27 on Windows using Python 3.12 and an optimized C++20
build. Both implementations consumed the same 100,000-event trace with seed 17.

| Implementation | Throughput | p50 | p95 | p99 |
|---|---:|---:|---:|---:|
| Python | 32,950 events/s | 8.4 us | 51.6 us | 108.1 us |
| C++20 | 235,062 events/s | 2.0 us | 3.0 us | 7.0 us |

The measured throughput ratio was **7.13x** in favor of C++ for this trace.
Both runs produced 78,909 trades and 20,931 active orders.

The raw snapshot is in
[`cpp-benchmark-results.csv`](cpp-benchmark-results.csv).

## Interpretation

The result supports a narrow conclusion: for this single-threaded in-memory
matching workload, the C++ implementation is materially faster while matching
the Python reference output.

It does not establish a universal 7x speedup. Results depend on compiler,
hardware, Python version, trace composition, sample size, and background load.
The benchmark should be rerun on the target machine, across several seeds and
workload regimes, before drawing stronger conclusions.
