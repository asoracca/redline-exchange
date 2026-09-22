# Measured API performance

Median of repeated runs; latency is measured in a separate pass. C++ includes the Python binding and conversion to the same Python value objects.

| Workload | Backend | Events/s | Trial min–max | p50 µs | p95 µs | p99 µs |
|---|---|---:|---:|---:|---:|---:|
| crossing | python | 283,217 | 279,929–286,083 | 2.46 | 8.04 | 11.75 |
| crossing | cpp | 430,584 | 423,498–433,807 | 1.33 | 6.21 | 8.38 |
| resting | python | 341,272 | 324,156–370,765 | 2.04 | 2.79 | 3.42 |
| resting | cpp | 965,018 | 916,882–1,024,922 | 0.92 | 1.54 | 1.92 |
| cancel_replace | python | 876,881 | 868,785–916,576 | 1.29 | 1.71 | 2.04 |
| cancel_replace | cpp | 1,139,952 | 1,083,188–1,156,958 | 0.83 | 1.62 | 1.96 |
| mixed | python | 272,991 | 262,745–275,243 | 2.71 | 8.08 | 11.71 |
| mixed | cpp | 396,570 | 393,899–399,086 | 1.88 | 6.29 | 8.50 |

Events/s equals orders/s only for crossing/resting (all submissions).

Environment: macOS-26.5.1-arm64-arm-64bit; Python 3.12.14.
Events per workload: 100,000; seed: 17; repeats: 5.
Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.

See results.json for individual trials, operation mix, latency by operation, compiler flags, input hashes, and parity digests. These synthetic, single-process measurements do not represent network or production-exchange latency.
