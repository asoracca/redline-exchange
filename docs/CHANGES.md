# File-by-file changes

Base: `0856f00d4ba198c1c6a15572d8b5a1e8b67f8917`.
The initial work was prepared on `codex/python-cpp-portfolio`. Shipping uses
`ship/python-cpp-improvements`; see [shipping validation](SHIPPING.md) for the
fresh build and measurements. The initial archives remain historical snapshots.

## Modified files

| File | Why |
|---|---|
| `README.md` | Present the five stages, measured comparison, chart, native quickstart and scope; preserve the original API/rules and research description |
| `src/orderbook/book.py` | Enforce integer prices and quantities, including replacements, before mutation |
| `pyproject.toml` | Add the optional pybind11 dependency and explicitly preserve the earlier Ruff default lint rule set across newer versions |
| `.gitignore` | Exclude native binaries, build metadata, regenerated benchmark/profile directories and binary profiler output |
| `.github/workflows/tests.yml` | Preserve original Python checks; add explicit native imports, parity tests, Linux sanitizer checks and comparison/profile smoke jobs for Python 3.11–3.13 |
| `docs/DESIGN.md` | Correct depth/heap complexity, explain retained state, and connect native implementation to profiling |
| `docs/BENCHMARKS.md` | Define prepared-input timing, repetitions, percentiles, units, equivalence checks, workloads, reproducibility and limitations |

## New implementation and validation files

| File | Why |
|---|---|
| `cpp/core.hpp` | Independent C++17 state, matching, cancellation, replacement, snapshots, numeric bounds and invariant accounting |
| `cpp/bindings.cpp` | Small pybind11 boundary exposing the core and compiler identity |
| `cpp/test_core.cpp` | Standalone FIFO/replacement/rejection/churn test, also runnable with sanitizers |
| `src/orderbook/native.py` | Python adapter returning existing dataclasses and consistent exceptions; Python stays the default |
| `src/orderbook/workloads.py` | Deterministic prepared events, shared dispatch/replay, input hashes and exact response/final-state verification |
| `scripts/build_native.py` | Optional release build with explicit flags and source/compiler metadata |
| `compare.py` | Independent throughput/latency passes, alternating repeated trials, parity gate, raw output and plot |
| `profile_matching.py` | Prepared replay cProfile rankings plus a separate tracemalloc pass |
| `tests/test_native.py` | Reuse original regressions; seeded workload parity, generated per-event state/depth/history parity and numeric boundaries |
| `tests/test_validation.py` | Reject invalid numeric types atomically on both backends; empty markets, side and ID checks |
| `tests/test_benchmarks.py` | Validate workload determinism and generated-event invariants |

## New documentation and evidence

| File | Why |
|---|---|
| `docs/NATIVE.md` | Build requirements, Python/C++ interface, bounds, complexity and native limitations |
| `docs/PROFILING.md` | Interpret actual function/allocation measurements and run variability |
| `docs/PORTFOLIO_AUDIT.md` | Current repo/profile findings, source links, specific recommendations for all other public repos, and validation scope |
| `docs/CODEX_SPEC.md` | Detailed reusable implementation/continuation prompt with acceptance criteria |
| `docs/CHANGES.md` | This complete change inventory |
| `docs/performance/results.json` | Every measured trial, per-operation latency, source/input hashes, parity digests and environment/build metadata |
| `docs/performance/results.csv` | Tabular raw trial measurements |
| `docs/performance/SUMMARY.md` | Median throughput and p50/p95/p99 table |
| `docs/performance/throughput.png` | Chart generated from the recorded trials; visually checked |
| `docs/profiling/profile.txt` | Actual self/cumulative cProfile rankings |
| `docs/profiling/memory.txt` | Actual Python traced allocation measurements, with scope stated |

## Initial validation and preservation — historical

- Original suite: **31 passed** before edits.
- Updated Python + native suite: **77 passed**; no native skips.
- Python-only source copy without the extension: **41 passed, 1 native-module
  skip**. The core Python package remains useful without a compiler.
- Editable installation with `.[dev,native,research]` succeeded.
- Original CLI, CSV replay and legacy benchmark smoke checks succeeded; the new
  Python-only benchmark path also completed.
- Standalone C++ checks passed on this Mac; Ruff lint and formatting passed.
- Final comparison: 100,000 events × four workloads × five trials per backend;
  every stream passed exact parity before timing. Throughput and latency are
  separate passes. Full raw evidence is retained, including a slow native trial.
- Hosted Linux CI/sanitizer execution remains unverified until this branch is
  pushed and its workflow runs. Local C++ standalone tests were unsanitized.

The original research, market lab, replay, examples, license, legacy benchmark
and all original test files are unchanged. Native binaries, `native-build.json`,
`matching.prof`, Python caches and editable-install metadata are generated locally
and ignored; rebuild them instead of committing machine-specific artifacts.

## Continuation changes

The follow-up retains the initial engine implementation and adds the following.
The newest source archive is `redline-exchange-continued.zip` and its patch is
`redline-continued.patch`; the initial archive is preserved as historical evidence.

| File | Follow-up change and reason |
|---|---|
| `src/orderbook/build_info.py` | New strict check that source hashes, Python ABI, metadata and loaded binary match before timing |
| `scripts/build_native.py` | Compile to a temporary artifact, record binary/ABI metadata, and preserve the previous build on compiler failure |
| `compare.py` | Require valid build provenance; use saved environment when reporting; show trial min/max; optional chart suppression; normalized CSV line endings |
| `study.py` | Run the existing comparison in separate processes for distinct seeds and reject incompatible/incomplete aggregation |
| `profile_matching.py` | Add structured profile metadata and normalize the text report |
| `tests/test_build_info.py` | Regression coverage for missing/invalid metadata, changed sources/binary, mismatched ABI and another checkout |
| `tests/test_reporting.py` | Verify nearest-rank percentiles, ratios of medians, saved-environment reporting and invalid study-input rejection |
| `.github/workflows/tests.yml` | Add a two-seed study smoke run to native CI |
| `README.md` | Refresh measured results and link the three-seed study |
| `docs/BENCHMARKS.md` | Document build checks, trial ranges and multiple-seed protocol |
| `docs/NATIVE.md` | Explain failure-safe builds and provenance checks |
| `docs/CODEX_SPEC.md` | Add continuation instructions for the new checks/study |
| `docs/PORTFOLIO_AUDIT.md` | Record rechecked README sources and follow-up findings |
| `docs/profile-readme-sources.json` | Current public README URLs and content hashes for all nine repos |
| `docs/CONTINUATION.md` | Follow-up outcome, scope, validation and measured interpretation |
| `docs/PROFILING.md` | Interpret the regenerated profile with current source metadata |
| `docs/performance/results.json` | Refresh every first-seed raw trial and strict build metadata |
| `docs/performance/results.csv` | Refresh the first-seed tabular trials |
| `docs/performance/SUMMARY.md` | Refresh first-seed medians, quantiles and trial ranges |
| `docs/performance/throughput.png` | Refresh the chart and add min/max trial whiskers |
| `docs/performance/study.json` | New per-seed ratios of medians |
| `docs/performance/STUDY.md` | Readable three-seed summary with links to raw evidence |
| `docs/performance/seed-42/results.json` | Full second-seed trials, provenance, operation mix and parity digests |
| `docs/performance/seed-42/results.csv` | Second-seed tabular trials |
| `docs/performance/seed-42/SUMMARY.md` | Second-seed medians, latency and ranges |
| `docs/performance/seed-73/results.json` | Full third-seed trials, provenance, operation mix and parity digests |
| `docs/performance/seed-73/results.csv` | Third-seed tabular trials |
| `docs/performance/seed-73/SUMMARY.md` | Third-seed medians, latency and ranges |
| `docs/profiling/profile.json` | New source/input hashes, environment, function timings and allocation metadata |
| `docs/profiling/profile.txt` | Regenerated self/cumulative function rankings |
| `docs/profiling/memory.txt` | Regenerated traced allocations |
| `docs/CHANGES.md` | Extend this inventory to cover every continuation file |

The validation above describes the initial delivery. The September 15 follow-up counts
and results are in `docs/CONTINUATION.md`; the current validation is in
[SHIPPING.md](SHIPPING.md).

## Shipping refresh

| File | Shipping change |
|---|---|
| `.gitignore` | Ignore `.DS_Store` while preserving the local Finder files |
| `README.md` | Replace previous timings with the 2026-09-21 run and identify hardware, date, compiler target and reproduction command |
| `docs/SHIPPING.md` | Record fresh environment/build/testing, compiler-target workaround and the new measurements |
| `docs/NATIVE.md` | Document the verified arm64 macOS compiler target |
| `docs/PROFILING.md` | Interpret the shipping profile instead of earlier timings |
| `docs/performance/` | Regenerate all 12 recorded workload/seed combinations, raw trials, summaries and chart |
| `docs/profiling/` | Regenerate profiling rankings, memory figures and source/environment metadata |
| `docs/CONTINUATION.md` | Mark the earlier continuation as historical and link shipping validation |
| `docs/PORTFOLIO_AUDIT.md` | Retain the dated audit and point publication readers to shipping validation |
| `docs/CHANGES.md` | Record this shipping refresh |
