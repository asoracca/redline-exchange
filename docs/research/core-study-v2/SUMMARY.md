# Measured API performance

Median of repeated runs; latency is measured in a separate pass. C++ includes the Python binding and conversion to the same Python value objects.

| Workload | Backend | Events/s | Trial min–max | p50 µs | p95 µs | p99 µs |
|---|---|---:|---:|---:|---:|---:|
| crossing | python | 275,783 | 269,497–276,947 | 2.58 | 8.33 | 12.75 |
| crossing | cpp | 397,237 | 392,352–398,881 | 1.54 | 6.29 | 9.21 |
| resting | python | 355,833 | 343,891–372,316 | 2.00 | 2.75 | 6.00 |
| resting | cpp | 881,648 | 738,416–907,699 | 1.00 | 1.79 | 2.29 |
| cancel_replace | python | 866,787 | 825,910–888,029 | 1.33 | 1.83 | 2.21 |
| cancel_replace | cpp | 1,112,556 | 1,108,382–1,125,559 | 0.83 | 1.58 | 1.75 |
| mixed | python | 270,005 | 262,262–270,573 | 2.62 | 8.12 | 12.17 |
| mixed | cpp | 372,461 | 148,643–389,555 | 2.00 | 6.42 | 9.46 |

Events/s equals orders/s only for crossing/resting (all submissions).

Environment: macOS-26.5.1-arm64-arm-64bit; Python 3.12.14.
Events per workload: 100,000; seed: 17; repeats: 5.
Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.

See results.json for individual trials, operation mix, latency by operation, compiler flags, input hashes, and parity digests. These synthetic, single-process measurements do not represent network or production-exchange latency.
