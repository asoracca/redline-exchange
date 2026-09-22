# Shipping validation — 2026-09-21

Branch: `ship/python-cpp-improvements`. Base:
`0856f00d4ba198c1c6a15572d8b5a1e8b67f8917`.
The prepared local changes were saved in a stash before switching branches and
then reapplied. The stash is retained as a backup. Finder metadata is preserved
locally and excluded via `.gitignore`.

## Clean environment and build

A new repository-local `.venv` was created with Python 3.12.14. The documented
editable installation of `.[dev,native,research]` and Zig 0.13.0 succeeded.

Measured host: Apple M5, 10 physical CPU cores, 16 GiB memory, macOS 26.5.1 arm64.
Compiler: Zig 0.13.0 / Clang 18.1.6. There is no CPU affinity or background-load
isolation. Installed benchmark dependency versions and full compiler flags are
in [results.json](performance/results.json).

```bash
python scripts/build_native.py --cxx 'python -m ziglang c++ -target aarch64-macos.14.0'
python -c 'from orderbook import _native; print(_native.compiler)'
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m ziglang c++ -target aarch64-macos.14.0 -std=c++17 -O2 \
  -Wall -Wextra -Wpedantic cpp/test_core.cpp -o build/redline-core-test
build/redline-core-test
```

The compiler's implicit macOS target failed to link the standalone executable on
this host. The explicit deployment target above resolved it; both the extension
and standalone test were rebuilt with that target. Linux CI uses its native
system compiler. CMake and mypy are not configured or required by this repository.

## Local checks completed

- Native extension built/imported successfully.
- **95 Python/native tests passed**, with no skipped native module.
- Standalone C++ core checks passed.
- Ruff lint and formatting passed.
- Module CLI, installed `redline-demo` and CSV replay example passed.
- Legacy 10,000-order benchmark and new Python-only comparison smoke passed.
- `run_market_lab.py` and the five-scenario, 50-seed `run_market_study.py` passed.
- Source/build provenance, parity digests, saved tables, and documentation links
  were checked before publication.

## New measurements

Dates in this document use America/Chicago; raw JSON timestamps use UTC
(2026-09-22 for this evening run).

```bash
python study.py --orders 100000 --repeats 5 --seeds 17 42 73 --output docs/performance
python profile_matching.py --orders 100000 --seed 17 --workload mixed --output docs/profiling
```

The study records 120 throughput trials with separate latency passes. Native
median throughput ranges from **1.29× to 2.83×** Python across workload/seed
pairs. Seed-17 crossing is **283,217 orders/s Python**
and **430,584 orders/s C++ through Python**. All numbers
were produced again for this shipping run; no earlier timings were reused.

[Study](performance/STUDY.md) · [Latency/ranges](performance/SUMMARY.md) ·
[Profiling](PROFILING.md)

## Publication and hosted checks

Local publication attempt: Git had no HTTPS credentials, and the connected
GitHub app rejected repository writes with HTTP 403 (`Resource not accessible
by integration`). Publishing and hosted CI therefore require GitHub write access.
No remote branch or pull request was created by that attempt.

This branch is intended for an open pull request against `main`, without merging.
The PR's Checks tab is the source of truth for hosted results. Linux CI includes
Python-only validation, native parity on Python 3.11/3.12/3.13, address/undefined-
behavior sanitizers, and benchmark/profile/study smoke runs. Local results above
do not substitute for those hosted checks.

The earlier audit and continuation documents describe the September 15 preparation
phase; this document and current performance files describe shipping validation.
