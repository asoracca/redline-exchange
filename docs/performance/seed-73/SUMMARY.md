# Measured API performance

Median of repeated runs; latency is measured in a separate pass. C++ includes the Python binding and conversion to the same Python value objects.

| Workload | Backend | Events/s | Trial min–max | p50 µs | p95 µs | p99 µs |
|---|---|---:|---:|---:|---:|---:|
| crossing | python | 262,213 | 259,106–279,142 | 2.62 | 8.42 | 12.42 |
| crossing | cpp | 408,010 | 394,605–412,188 | 1.71 | 6.42 | 8.71 |
| resting | python | 347,358 | 318,188–358,012 | 2.04 | 3.08 | 4.08 |
| resting | cpp | 825,825 | 748,994–950,849 | 1.00 | 2.08 | 2.67 |
| cancel_replace | python | 868,362 | 852,068–869,844 | 1.33 | 1.83 | 2.33 |
| cancel_replace | cpp | 1,137,286 | 1,125,267–1,144,628 | 0.83 | 1.54 | 1.75 |
| mixed | python | 258,502 | 247,019–266,320 | 2.92 | 8.75 | 12.54 |
| mixed | cpp | 386,825 | 377,991–390,881 | 2.00 | 6.33 | 9.04 |

Events/s equals orders/s only for crossing/resting (all submissions).

Environment: macOS-26.5.1-arm64-arm-64bit; Python 3.12.14.
Events per workload: 100,000; seed: 73; repeats: 5.
Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.

See results.json for individual trials, operation mix, latency by operation, compiler flags, input hashes, and parity digests. These synthetic, single-process measurements do not represent network or production-exchange latency.
