# Measured API performance

Median of repeated runs; latency is measured in a separate pass. C++ includes the Python binding and conversion to the same Python value objects.

| Workload | Backend | Events/s | Trial min–max | p50 µs | p95 µs | p99 µs |
|---|---|---:|---:|---:|---:|---:|
| crossing | python | 276,397 | 275,060–277,008 | 2.67 | 8.25 | 11.75 |
| crossing | cpp | 429,786 | 414,801–439,225 | 1.42 | 6.33 | 8.83 |
| resting | python | 352,880 | 332,393–373,845 | 2.04 | 2.92 | 3.62 |
| resting | cpp | 926,545 | 903,219–1,035,219 | 0.96 | 1.62 | 2.00 |
| cancel_replace | python | 856,352 | 849,656–862,814 | 1.29 | 1.79 | 2.29 |
| cancel_replace | cpp | 1,150,369 | 1,124,489–1,189,846 | 0.83 | 1.58 | 1.96 |
| mixed | python | 272,199 | 268,592–275,511 | 2.71 | 8.12 | 11.50 |
| mixed | cpp | 399,599 | 386,235–401,263 | 1.83 | 6.25 | 8.21 |

Events/s equals orders/s only for crossing/resting (all submissions).

Environment: macOS-26.5.1-arm64-arm-64bit; Python 3.12.14.
Events per workload: 100,000; seed: 42; repeats: 5.
Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.

See results.json for individual trials, operation mix, latency by operation, compiler flags, input hashes, and parity digests. These synthetic, single-process measurements do not represent network or production-exchange latency.
