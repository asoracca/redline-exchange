# What the profile shows

Re-measured 2026-09-21 on the [shipping environment](SHIPPING.md), with 100,000
prepared mixed events, seed 17 and history disabled. [Raw rankings](profiling/profile.txt),
[structured provenance](profiling/profile.json), and [allocations](profiling/memory.txt).

| Python function | Self time (s) | Cumulative time (s) |
|---|---:|---:|
| `_match` | 0.195 | 0.573 |
| `_new_order` | 0.198 | 0.262 |
| `_discard_stale_top` | 0.107 | 0.191 |
| `_best_opposite` | 0.047 | 0.151 |

These are instrumented cProfile times; cumulative values overlap. Matching,
new-order bookkeeping and stale-heap cleanup remain the key observed Python
costs. The native scope covers matching state and order bookkeeping, while
research orchestration remains in Python. This shipping validation introduces
no additional matching-engine optimization.

The separate tracemalloc pass retained **10,258,214 bytes**, with
**11,984,326 bytes** at peak and **6,800 active orders**.
Prepared input creation is excluded. These are traced Python allocations, not
RSS or native memory. Lifetime seen IDs, max-quantity accounting and stale heap
entries mean memory is not bounded by active order count.

Depth snapshots are outside this matching workload. Their full-book aggregation
is a candidate for separate measurement, not a demonstrated hotspot here.

The current [three-seed study](performance/STUDY.md) measured native/Python median
throughput ratios from 1.29× to 2.83×. Every trial is retained, including slower
ones, and trial ranges are reported. Differences from earlier runs do not prove
an engine improvement; hardware scheduling, allocation and thermal effects were
not individually controlled. Multiple input seeds on one machine do not establish
cross-hardware confidence intervals. The cancel/replace stream is fixed across
seeds, so its repetitions measure run variability only.
