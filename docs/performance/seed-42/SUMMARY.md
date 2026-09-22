# Measured API performance

Median of repeated runs; latency is measured in a separate pass. C++ includes the Python binding and conversion to the same Python value objects.

| Workload | Backend | Events/s | Trial min–max | p50 µs | p95 µs | p99 µs |
|---|---|---:|---:|---:|---:|---:|
| crossing | python | 278,985 | 269,827–284,158 | 2.58 | 8.21 | 12.21 |
| crossing | cpp | 407,039 | 354,696–416,851 | 1.50 | 6.25 | 8.83 |
| resting | python | 347,500 | 328,280–375,412 | 2.00 | 2.88 | 3.54 |
| resting | cpp | 905,102 | 867,276–936,705 | 0.96 | 1.62 | 1.96 |
| cancel_replace | python | 903,492 | 885,968–921,999 | 1.29 | 1.71 | 2.25 |
| cancel_replace | cpp | 1,169,512 | 1,142,119–1,198,166 | 0.83 | 1.54 | 1.75 |
| mixed | python | 265,974 | 255,455–269,820 | 2.83 | 8.50 | 12.25 |
| mixed | cpp | 380,108 | 379,277–388,813 | 2.33 | 6.46 | 9.08 |

Events/s equals orders/s only for crossing/resting (all submissions).

Environment: macOS-26.5.1-arm64-arm-64bit; Python 3.12.14.
Events per workload: 100,000; seed: 42; repeats: 5.
Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.

See results.json for individual trials, operation mix, latency by operation, compiler flags, input hashes, and parity digests. These synthetic, single-process measurements do not represent network or production-exchange latency.
