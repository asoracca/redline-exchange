# Measured API performance

Median of repeated runs; latency is measured in a separate pass. C++ includes the Python binding and conversion to the same Python value objects.

| Workload | Backend | Events/s | Trial min–max | p50 µs | p95 µs | p99 µs |
|---|---|---:|---:|---:|---:|---:|
| crossing | python | 267,819 | 264,230–279,885 | 2.46 | 8.54 | 13.75 |
| crossing | cpp | 382,064 | 354,316–416,561 | 1.46 | 6.33 | 10.04 |
| resting | python | 377,704 | 333,047–379,322 | 1.96 | 2.58 | 4.04 |
| resting | cpp | 853,339 | 725,867–910,150 | 1.00 | 1.67 | 2.29 |
| cancel_replace | python | 886,311 | 875,163–907,215 | 1.29 | 1.75 | 2.00 |
| cancel_replace | cpp | 1,150,222 | 1,121,599–1,172,373 | 0.79 | 1.54 | 1.62 |
| mixed | python | 262,158 | 259,702–264,323 | 2.67 | 8.33 | 12.38 |
| mixed | cpp | 381,351 | 378,293–388,290 | 1.96 | 6.25 | 9.12 |

Events/s equals orders/s only for crossing/resting (all submissions).

Environment: macOS-26.5.1-arm64-arm-64bit; Python 3.12.14.
Events per workload: 100,000; seed: 73; repeats: 5.
Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.

See results.json for individual trials, operation mix, latency by operation, compiler flags, input hashes, and parity digests. These synthetic, single-process measurements do not represent network or production-exchange latency.
