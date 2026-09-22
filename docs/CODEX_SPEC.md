# Redline Exchange: implementation and continuation spec

Copy the following specification into a coding task with access to
`https://github.com/asoracca/redline-exchange`. It is intentionally independent
of any particular Codex model or product setting.

---

Improve Redline Exchange into a rigorous freshman SWE/quant portfolio project
covering V1 Python CLOB, V2 benchmarks, V3 profiling, V4 C++ matching core and V5
an honest Python-versus-C++ comparison. Work in the repository, inspect its actual
state first, and preserve existing good work. If these stages already exist,
validate and continue them instead of replacing them with a second engine.

## Inspect before editing

1. Read applicable repository instructions, README, design notes, public API,
   tests, benchmarks, replay, and market research modules. Check branch/status and
   preserve user changes. Create a `codex/` branch when appropriate.
2. Record the starting revision and run the existing tests before modifying
   behavior. Inspect any existing native code and results before generating new
   versions. Do not invent tests passed or performance numbers.
3. Keep research/simulation in Python. Keep the default backend working without
   a C++ compiler. Separate native state/matching logic from Python bindings.
4. Audit https://github.com/asoracca and current READMEs/file inventories for the
   remaining public repos. Distinguish direct code findings from README claims.
   Give repo-specific priorities, not generic “add tests” advice where tests exist.

## V1: Python reference engine

Preserve `LimitOrderBook`, `Side`, `Order`, `Trade`, `BookLevel`, the CLI, CSV
replay, original tests, market lab and multi-seed research. Retain:

- single-symbol limit and market orders, buy/sell, positive integer ticks;
- price priority then arrival sequence; maker-price executions;
- partial fills, multi-level sweeps and unfilled market residual cancellation;
- lifetime-unique order IDs and cancellation by active ID;
- replace quantity defined as new remaining quantity: same-price reduction/equal
  quantity keeps priority; increase or reprice loses it and can cross;
- detached snapshots, depth, top of book, spread, midpoint and optional history;
- invariant checks and deterministic replay.

Reject floats, booleans, NaN and infinity for prices/quantities before mutation.
Keep error behavior explicit. Add regression tests for invalid-state atomicity.
Do not silently accept unsupported order types or change replay formats.

## V2: reproducible benchmarks

Pre-generate the exact event stream, seed and IDs outside timing. Use the same
stream for every backend. Include crossing submissions, non-crossing growing
books, cancel/replace churn and a mixed stream with limits/markets/cancels/replaces.
Record actual operation counts rather than claiming nominal percentages.

Use fresh books and separate throughput and per-event-latency passes. Warm each
backend, keep equivalent history settings, and alternate trial order. Default to
at least five trials. Report events/s (orders/s only for submission-only streams),
p50, p95 and p99 in microseconds; document the quantile method and timer overhead.
Report per-operation latency when a workload mixes operations. Include raw JSON,
CSV, a readable summary and an optional chart derived directly from those results.

Persist OS/architecture, Python/dependency/compiler versions, compiler flags,
clock metadata, GC policy, seed, event count, trial index, source hash, input hash
and correctness digests. Do not include preparation, parsing, validation,
charting or profiling in a throughput figure. Do not mix old end-to-end benchmark
numbers with the new prepared-stream measurements. Keep the old entrypoint usable.

## V3: evidence-driven profiling

Use cProfile on prepared Python replay. Save both self-time and cumulative-time
rankings and a reloadable profile file. Run Python allocation tracing separately.
Explain observed bottlenecks, not assumed ones. Distinguish traced Python bytes
from RSS/native memory, and profiling timings from benchmark timings. Explain
retained seen-ID/accounting maps and lazy-heap entries even with history disabled.
Connect the measured hotspots to the C++ scope and future optimization candidates.

## V4: C++17 matching core

Keep the core independent of Python headers; use pybind11 only in a small binding
file and a Python adapter. Match the Python-facing return objects and semantics.
Use integer ticks, explicit bounds and checked arithmetic at the boundary.
Reject out-of-range values instead of wrapping. Document any difference from
Python arbitrary-precision integers and the range for parity.

Prefer a clear implementation of the reference data structures first: bid/ask
priority queues, active-order hash map, sequence/ID stale-entry protection,
lifetime seen IDs and accounting used for invariants. Do not simultaneously
change matching policy, benchmark workload and data structure without isolating
those effects. Keep equivalent history policy and observable outputs.

Build with a documented release command. Include an optional standalone core
test and Linux address/undefined-behavior sanitizer configuration. Building should
fail clearly; missing native code must not silently produce a “C++” result.
Document platform prerequisites and how to rebuild after changing Python versions.

## V5: parity first, comparison second

Before every performance comparison, compare all returned trades/cancel snapshots
and final full active state/history against Python on the complete input stream.
Add randomized tests comparing state and depth after each event, plus regression
coverage for FIFO, better prices, partial fills, stale replacement entries,
priority retention/loss, missing/duplicate IDs, empty books, numeric boundaries,
unchanged state after rejected inputs, and history disabled.

Report API-to-API results with the native binding and Python materialization costs
included. If adding a standalone native benchmark, label it separately. Show
ratios of medians for identical workloads and preserve unfavorable findings.
No fabricated, borrowed, projected, exchange-grade or nanosecond claims.
Record limitations: synthetic input, no network/persistence, no CPU pinning unless
actually performed, background/thermal noise, and finite single-threaded scope.

## Deliverables and acceptance

- Clean README with a small example, V1–V5 map, reproducible setup, results table
  or chart, matching rules, architecture links and candid limitations.
- Native build helper; tests; benchmark and profile scripts; raw measured output;
  design, interface and methodology documentation.
- CI that preserves original checks and explicitly imports native code before
  running parity tests, so accidental skips cannot look like native success.
- Concise repository/profile audit with current sources and prioritized fixes.
- Every changed/new file listed with its purpose and validation status.
- No changes to unrelated repos/profile metadata without task authorization.
- Full tests and lint pass; native tests actually execute; regenerate measured
  results after source changes; verify the chart/table against raw data.
- Distinguish local implementation from pushed commits, PRs, merged code and
  hosted CI. Package a patch or source archive if work remains local.

## Continuing the delivered implementation

Start with `docs/PORTFOLIO_AUDIT.md`, `docs/CHANGES.md`, `docs/NATIVE.md`,
`docs/BENCHMARKS.md`, `docs/performance/results.json`, and `docs/PROFILING.md`.
Run `python -m pytest -q`, rebuild native, then rerun parity and the comparison.

Useful next experiments, after reading the evidence:

1. Test multiple seeds and larger sizes; report spread and memory growth.
2. Measure incremental price-level depth separately before optimizing research
   snapshot access; it was not timed in the matching benchmark.
3. Compare heap compaction against lazy cancellation on long-lived churn streams.
4. Add a batched binding/standalone C++ benchmark, clearly separate from the
   existing API comparison and with output-parity tests.
5. Review and publish the local branch when requested; verify hosted CI before
   calling the public repository complete.

Do not add speculative trading strategies, exchange networking, or a new UI just
to enlarge the project. Prioritize work the owner can demonstrate and explain.

## Continuation delivered after the initial implementation

A follow-up now adds strict binary/source/Python build provenance and a three-seed
study. Read `docs/CONTINUATION.md` for the new findings and validation, and use
`python study.py --orders 100000 --repeats 5 --seeds 17 42 73` to repeat it.
Do not regress these guards or combine results from different builds/environments.
