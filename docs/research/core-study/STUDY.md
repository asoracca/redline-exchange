# Comparison across seeds

100,000 events per workload; 5 trials per backend and seed.
Each seed runs in a fresh process; matching rules and API timing are unchanged.

| Seed | Workload | Python events/s | C++ events/s | Ratio of medians |
|---:|---|---:|---:|---:|
| 17 | crossing | 277,118 | 432,067 | 1.56× |
| 17 | resting | 336,298 | 932,937 | 2.77× |
| 17 | cancel_replace | 883,729 | 1,151,043 | 1.30× |
| 17 | mixed | 262,463 | 387,315 | 1.48× |
| 42 | crossing | 276,397 | 429,786 | 1.55× |
| 42 | resting | 352,880 | 926,545 | 2.63× |
| 42 | cancel_replace | 856,352 | 1,150,369 | 1.34× |
| 42 | mixed | 272,199 | 399,599 | 1.47× |
| 73 | crossing | 286,956 | 423,898 | 1.48× |
| 73 | resting | 339,595 | 936,173 | 2.76× |
| 73 | cancel_replace | 904,506 | 1,134,009 | 1.25× |
| 73 | mixed | 272,596 | 402,993 | 1.48× |

These are input-seed checks on one host, not confidence intervals across hardware.
The cancel/replace stream is deliberately identical across seeds; its repeats test
run variability, not input diversity. No trial is dropped.

The first seed uses [results.json](results.json) and [SUMMARY.md](SUMMARY.md).
- Seed 42: [raw trials](seed-42/results.json) · [table](seed-42/SUMMARY.md)
- Seed 73: [raw trials](seed-73/results.json) · [table](seed-73/SUMMARY.md)

Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.
