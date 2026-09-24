# Comparison across seeds

100,000 events per workload; 5 trials per backend and seed.
Each seed runs in a fresh process; matching rules and API timing are unchanged.

| Seed | Workload | Python events/s | C++ events/s | Ratio of medians |
|---:|---|---:|---:|---:|
| 17 | crossing | 275,783 | 397,237 | 1.44× |
| 17 | resting | 355,833 | 881,648 | 2.48× |
| 17 | cancel_replace | 866,787 | 1,112,556 | 1.28× |
| 17 | mixed | 270,005 | 372,461 | 1.38× |
| 42 | crossing | 262,370 | 367,726 | 1.40× |
| 42 | resting | 361,787 | 910,734 | 2.52× |
| 42 | cancel_replace | 848,995 | 1,100,172 | 1.30× |
| 42 | mixed | 261,560 | 377,529 | 1.44× |
| 73 | crossing | 267,819 | 382,064 | 1.43× |
| 73 | resting | 377,704 | 853,339 | 2.26× |
| 73 | cancel_replace | 886,311 | 1,150,222 | 1.30× |
| 73 | mixed | 262,158 | 381,351 | 1.45× |

These are input-seed checks on one host, not confidence intervals across hardware.
The cancel/replace stream is deliberately identical across seeds; its repeats test
run variability, not input diversity. No trial is dropped.

The first seed uses [results.json](results.json) and [SUMMARY.md](SUMMARY.md).
- Seed 42: [raw trials](seed-42/results.json) · [table](seed-42/SUMMARY.md)
- Seed 73: [raw trials](seed-73/results.json) · [table](seed-73/SUMMARY.md)

Source SHA-256: `2465ab3c066be4b88dfadcb2b70970b871813c5c78975cbff3bc383353edaed5`.
