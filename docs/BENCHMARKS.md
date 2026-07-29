# Benchmark methodology

`benchmark.py` submits a reproducible stream of crossing limit orders around a
fixed midpoint. Random input generation is included in end-to-end throughput,
while per-order latency measures only the `submit_limit` call.

Run the standard sizes with:

```bash
python benchmark.py --orders 10000 100000 1000000 --csv benchmark-results.csv
```

The report includes:

- total elapsed time and orders per second;
- median (`p50`) submission latency;
- tail (`p95`) submission latency;
- trade count and active order count, which help characterize the workload.

Trade-history retention is disabled only for the benchmark so a one-million
event run measures matching rather than the memory cost of keeping an audit
ledger. Normal books retain their complete trade history.

Numbers depend on the Python version, operating system, CPU, and background
load. Compare implementations using the same seed and workload rather than
presenting one machine's result as universal exchange performance.

## Reference run

Recorded on 2026-07-18 using Python 3.12.13 on Windows and an Intel Core
i3-1115G4. These numbers are a reproducibility snapshot, not a performance
guarantee.

| Orders | Throughput | p50 | p95 |
|---:|---:|---:|---:|
| 10,000 | 26,414 orders/s | 12.9 us | 48.9 us |
| 100,000 | 29,482 orders/s | 12.6 us | 48.4 us |
| 1,000,000 | 28,107 orders/s | 13.2 us | 50.5 us |

The complete values are stored in [`benchmark-results.csv`](benchmark-results.csv).
