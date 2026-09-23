# Measured API performance

Median of repeated runs; latency is measured in a separate pass. C++ includes the Python binding and conversion to the same Python value objects.

| Workload | Backend | Events/s | Trial min–max | p50 µs | p95 µs | p99 µs |
|---|---|---:|---:|---:|---:|---:|
| crossing | python | 277,118 | 274,201–279,556 | 2.62 | 8.17 | 11.92 |
| crossing | cpp | 432,067 | 406,755–433,614 | 1.42 | 6.33 | 8.75 |
| resting | python | 336,298 | 330,354–383,203 | 2.04 | 2.92 | 3.58 |
| resting | cpp | 932,937 | 902,132–1,050,549 | 0.92 | 1.62 | 2.04 |
| cancel_replace | python | 883,729 | 880,946–910,931 | 1.29 | 1.75 | 2.25 |
| cancel_replace | cpp | 1,151,043 | 1,128,250–1,202,818 | 0.83 | 1.54 | 1.71 |
| mixed | python | 262,463 | 261,793–271,800 | 2.75 | 8.25 | 11.62 |
| mixed | cpp | 387,315 | 354,024–400,548 | 2.33 | 6.50 | 9.04 |

Events/s equals orders/s only for crossing/resting (all submissions).

Environment: macOS-26.5.1-arm64-arm-64bit; Python 3.12.14.
Events per workload: 100,000; seed: 17; repeats: 5.
Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.

See results.json for individual trials, operation mix, latency by operation, compiler flags, input hashes, and parity digests. These synthetic, single-process measurements do not represent network or production-exchange latency.
