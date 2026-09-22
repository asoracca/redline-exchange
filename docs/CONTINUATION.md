# Continuation: provenance and repeatability

> Historical preparation record from 2026-09-15. For the current build, measurements
> and publication validation, see [SHIPPING.md](SHIPPING.md).


## What changed

The five-stage Python/C++ implementation was already present. This follow-up
validated it, preserved the matching/research code, and addressed a concrete
reproducibility gap: the prior benchmark accepted missing build metadata and did
not verify that metadata described the loaded C++ binary.

Native timing now requires matching source hashes, binary checksum and location,
Python ABI/cache tag, compiler metadata and schema. The build helper compiles to
a temporary output so compiler failures preserve the previous working build.
The reporting code now uses saved environment details and displays trial ranges.

The new `study.py` runs seeds 17, 42 and 73 in fresh processes using the existing
comparison, preserving exact parity checks and the API timing boundary. The
profiler also records source/input hashes and structured measurements.

## Measured outcome

100,000 events per workload, five trials for each backend and each of three seeds:
**120 raw throughput trials**, with separate latency passes. Every complete input
stream passed output/final-state parity first. Native median throughput was
**1.30×–2.84×** Python across the twelve workload/seed pairs.

The seed-17 crossing result was **277,738 orders/s
Python** and **428,273 orders/s C++ via Python**.
Binding and Python result conversion remain included. No network, persistence or
CPU pinning is claimed. No raw trial was discarded.

[Full study](performance/STUDY.md) · [Latency/ranges](performance/SUMMARY.md) ·
[Profile evidence](PROFILING.md)

## Verification actually performed

- Before continuation: **77 tests passed** on the delivered implementation.
- After continuation and native rebuild: **95 tests passed** with native enabled.
- Python-only source copy: **59 passed, 1 expected native-module skip**.
- Standalone C++ core checks passed locally.
- Ruff lint and format checks passed.
- The old metadata was rejected before timing; nine invalid/stale provenance
  conditions and saved-data reporting have regression coverage.
- A simulated compiler failure left both binary and metadata byte-identical;
  the provenance guard accepted that preserved working build afterward.
- All three seeds ran with the same source and environment; aggregation checks
  protocol compatibility, complete trial sets and distinct seeds.
- Hosted Linux sanitizer/Python-matrix CI is configured, including a study smoke
  job, but has not been run on GitHub in this task.

## Scope and delivery

The preparation was based on commit
`0856f00d4ba198c1c6a15572d8b5a1e8b67f8917`.
The initial archive is preserved. The continued source archive and patch include
this follow-up, with every file explained in [CHANGES.md](CHANGES.md).

Next experiments can isolate memory growth under sustained churn, depth-heavy
research or batching; none is presented as a result already measured here.
