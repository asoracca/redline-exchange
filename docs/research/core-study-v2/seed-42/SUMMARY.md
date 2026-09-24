# Measured API performance

Median of repeated runs; latency is measured in a separate pass. C++ includes the Python binding and conversion to the same Python value objects.

| Workload | Backend | Events/s | Trial min–max | p50 µs | p95 µs | p99 µs |
|---|---|---:|---:|---:|---:|---:|
| crossing | python | 262,370 | 219,854–271,759 | 2.71 | 9.54 | 14.75 |
| crossing | cpp | 367,726 | 289,017–391,319 | 1.54 | 6.38 | 10.00 |
| resting | python | 361,787 | 343,385–378,060 | 2.00 | 2.67 | 4.92 |
| resting | cpp | 910,734 | 683,339–939,899 | 0.96 | 1.62 | 2.21 |
| cancel_replace | python | 848,995 | 791,285–873,380 | 1.33 | 1.71 | 2.04 |
| cancel_replace | cpp | 1,100,172 | 1,002,260–1,142,434 | 0.83 | 1.54 | 1.96 |
| mixed | python | 261,560 | 259,811–264,690 | 2.67 | 8.29 | 12.25 |
| mixed | cpp | 377,529 | 373,467–389,571 | 1.96 | 6.25 | 9.17 |

Events/s equals orders/s only for crossing/resting (all submissions).

Environment: macOS-26.5.1-arm64-arm-64bit; Python 3.12.14.
Events per workload: 100,000; seed: 42; repeats: 5.
Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.

See results.json for individual trials, operation mix, latency by operation, compiler flags, input hashes, and parity digests. These synthetic, single-process measurements do not represent network or production-exchange latency.
