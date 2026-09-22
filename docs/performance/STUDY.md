# Comparison across seeds

100,000 events per workload; 5 trials per backend and seed.
Each seed runs in a fresh process; matching rules and API timing are unchanged.

| Seed | Workload | Python events/s | C++ events/s | Ratio of medians |
|---:|---|---:|---:|---:|
| 17 | crossing | 283,217 | 430,584 | 1.52× |
| 17 | resting | 341,272 | 965,018 | 2.83× |
| 17 | cancel_replace | 876,881 | 1,139,952 | 1.30× |
| 17 | mixed | 272,991 | 396,570 | 1.45× |
| 42 | crossing | 278,985 | 407,039 | 1.46× |
| 42 | resting | 347,500 | 905,102 | 2.60× |
| 42 | cancel_replace | 903,492 | 1,169,512 | 1.29× |
| 42 | mixed | 265,974 | 380,108 | 1.43× |
| 73 | crossing | 262,213 | 408,010 | 1.56× |
| 73 | resting | 347,358 | 825,825 | 2.38× |
| 73 | cancel_replace | 868,362 | 1,137,286 | 1.31× |
| 73 | mixed | 258,502 | 386,825 | 1.50× |

These are input-seed checks on one host, not confidence intervals across hardware.
The cancel/replace stream is deliberately identical across seeds; its repeats test
run variability, not input diversity. No trial is dropped.

The first seed uses [results.json](results.json) and [SUMMARY.md](SUMMARY.md).
- Seed 42: [raw trials](seed-42/results.json) · [table](seed-42/SUMMARY.md)
- Seed 73: [raw trials](seed-73/results.json) · [table](seed-73/SUMMARY.md)

Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.
