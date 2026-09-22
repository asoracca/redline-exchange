# Benchmark and profiling protocol

## Reproduce the comparison

```bash
python -m pip install -e '.[dev,native,research]'
python scripts/build_native.py
python compare.py --orders 100000 --repeats 5 --seed 17 --output benchmark-results
python profile_matching.py --orders 100000 --seed 17 --workload mixed --output profile-results
```

For Python-only use: `python compare.py --python-only`. Missing native code
otherwise fails explicitly. Plotting is optional; install the research extra for
PNG output. Raw JSON/CSV and the Markdown table do not depend on matplotlib.

[Recorded results](performance/SUMMARY.md) · [raw trials](performance/results.csv)
· [full metadata](performance/results.json) · [profile](profiling/profile.txt)

## What is measured

1. Generate a deterministic event stream with a fixed seed **before timing**.
   Persist its hash and actual operation counts. Both engines see identical inputs.
2. Verify each returned order/trade and the final complete active state and trade
   history against Python. This pass is untimed and retains history.
3. Warm both backends on a prefix, then create a fresh empty book for each pass.
4. Measure throughput with a single outer timer over dispatch, matching, Python
   result construction, and counting trades. No random generation, disk IO,
   charting, snapshots, invariant checking, or per-event timers are in this pass.
5. Measure p50/p95/p99 with individual timers in a **separate fresh-book pass**.
   Percentiles use nearest rank, reported in microseconds. Timer/dispatch overhead
   is included, not subtracted. These are synchronous service times, not queueing,
   wire, or end-to-end exchange latency.
6. Run five trials, alternating backend order. GC stays in its current mode
   (enabled in the recorded run); collect before each pass. History is disabled
   equally in timed runs. Input preparation and book teardown are untimed.
7. Publish medians and retain every trial. JSON also has per-operation latency,
   clock details, package/compiler versions and flags, source and input hashes.

The existing `benchmark.py` is retained for backwards compatibility. Its
throughput includes random generation and its latency timer is inside that same
run. Its results must not be placed alongside `compare.py` results as equivalent
measurements.

## Workloads

| Name | Purpose | Unit |
|---|---|---|
| crossing | Random buy/sell limits around 10,000, 41 possible prices, sizes 1–500 | orders/s |
| resting | Non-crossing adds across 100 prices per side; growing book | orders/s |
| cancel_replace | Repeated add → reduce → increase/reprice → cancel cycles | events/s |
| mixed | Seeded limits, markets, and cancel/replace attempts on earlier IDs; inactive targets become adds | events/s |

The mixed stream is submission-heavy; JSON gives its actual mix. It is not a
claim to model observed exchange traffic. Cancel/replace is a deliberate churn
stress, not realistic queue depth. All books start empty; warmup uses a different
book. Change seeds, size, and shape to test whether a conclusion generalizes.

## Interpretation and limitations

- Speedup is the ratio of median throughput, C++ divided by Python, for the same
  workload/count/seed/environment. It is not the ratio of unrelated best trials.
- The Python API/binding is part of the C++ number. A future standalone native
  benchmark must be presented separately, with equivalent event preparation and
  outputs; do not label its speedup as a pure language effect.
- Python uses arbitrary integers and a dictionary/heap; native uses bounded
  integers and C++ containers. This measures implementations, not just syntax.
- The host is not isolated or CPU-pinned; thermal state, scheduling and background
  activity were not controlled. Short runs and p99 are noisy. Repeat on the target
  machine and inspect trial spread before putting a number on a resume.
- No network costs, persistence, queueing, multithread scaling, or exchange-grade
  latency conclusions follow from these synthetic tests.
- Five runs are repeated measurements, not a confidence interval across hardware.

## Profiling

`profile_matching.py` runs cProfile only on prepared replay, writes cumulative
and self-time rankings, then uses a separate tracemalloc pass for Python retained
and peak traced allocations. Input creation is excluded. `.prof` binary files are
ignored and can be regenerated for an interactive profiler; text reports are
versioned. Tracemalloc does not measure C++ allocations or whole-process RSS.

Profile timings include instrumentation overhead and are **not** performance
numbers. Cumulative times overlap; do not sum parent and child functions.
Use [profiling findings](PROFILING.md) to connect observed costs to design choices.

## Build provenance and repeated seeds

The comparison now requires `native-build.json` with the current schema, source
hashes, Python ABI/cache tag and checksum of the actual loaded extension. A
missing, incomplete or stale record fails before workload preparation/timing.
Loading an extension from another checkout also fails. Run the native build
helper to regenerate both binary and metadata. Python-only runs need neither.

This checks that the measured binary belongs to the recorded build; it is not a
cryptographic certification by a third party. Build metadata records compiler
flags and command, including the temporary output path used during compilation.

```bash
python study.py --orders 100000 --repeats 5 --seeds 17 42 73 --output benchmark-results
```

Each seed launches the existing comparison in a fresh Python process, preserving
its parity checks and timing protocol. The first seed writes the normal output
files; additional seeds use `seed-<number>/`. `STUDY.md` and `study.json` report
ratios of per-backend medians for each workload/seed. Aggregation rejects different
source hashes, environments, protocols, duplicate seeds and missing/duplicate
trials. Trial ranges appear in the table and chart; they are not confidence
intervals. The cancel/replace workload is identical across seeds by design.

Use `--no-chart` with `compare.py` for raw JSON/CSV/Markdown only. Reporting removes
an older generated chart in that output directory so it cannot look current.
The Markdown table uses the environment saved with the results, not the Python
version on the machine re-rendering the table.

[Three-seed results](performance/STUDY.md) · [study data](performance/study.json)

Profiling also saves `profile.json` with source/input hashes, timestamp,
environment, function timings and traced allocations. Regenerate profiles after
changing source. Its measurements still describe instrumented Python execution.
