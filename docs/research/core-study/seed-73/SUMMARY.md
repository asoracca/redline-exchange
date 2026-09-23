# Measured API performance

Median of repeated runs; latency is measured in a separate pass. C++ includes the Python binding and conversion to the same Python value objects.

| Workload | Backend | Events/s | Trial min–max | p50 µs | p95 µs | p99 µs |
|---|---|---:|---:|---:|---:|---:|
| crossing | python | 286,956 | 284,651–298,536 | 2.58 | 8.04 | 11.21 |
| crossing | cpp | 423,898 | 418,556–441,361 | 1.42 | 6.25 | 8.62 |
| resting | python | 339,595 | 337,108–411,867 | 2.04 | 2.88 | 3.54 |
| resting | cpp | 936,173 | 912,116–1,055,977 | 0.96 | 1.58 | 1.96 |
| cancel_replace | python | 904,506 | 887,254–929,403 | 1.29 | 1.71 | 2.25 |
| cancel_replace | cpp | 1,134,009 | 1,132,820–1,203,928 | 0.83 | 1.58 | 2.00 |
| mixed | python | 272,596 | 264,505–284,949 | 2.62 | 7.96 | 11.29 |
| mixed | cpp | 402,993 | 391,837–410,464 | 2.29 | 6.38 | 8.67 |

Events/s equals orders/s only for crossing/resting (all submissions).

Environment: macOS-26.5.1-arm64-arm-64bit; Python 3.12.14.
Events per workload: 100,000; seed: 73; repeats: 5.
Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.

See results.json for individual trials, operation mix, latency by operation, compiler flags, input hashes, and parity digests. These synthetic, single-process measurements do not represent network or production-exchange latency.
