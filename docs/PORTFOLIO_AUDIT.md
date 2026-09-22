# Repository and profile audit

> Historical preparation record from 2026-09-15. For the current build, measurements
> and publication validation, see [SHIPPING.md](SHIPPING.md).


Reviewed 2026-09-15. Implementation starts from
`asoracca/redline-exchange` main commit
`0856f00d4ba198c1c6a15572d8b5a1e8b67f8917`.

## Scope and outcome

The [CLOB repository is redline-exchange](https://github.com/asoracca/redline-exchange).
Its Python source, tests, benchmark, build configuration, and design/README were
reviewed locally. For the other eight public repositories, this audit inspected
current README contents and recursive file inventories, not every implementation
or live deployment. Recommendations below are scoped to that evidence.

The implementation was prepared on `codex/python-cpp-portfolio` before publication. The existing Python architecture, replay, market
lab, research results, license, and original regression tests are preserved.

## CLOB: what was already good

- A focused Python package with a small public API and detached snapshots.
- Bid/ask heaps plus an active-order dictionary; price/sequence/ID heap keys
  correctly protect against stale entries after cancel/replace.
- Explicit maker-price execution, price-time priority, market residual handling,
  single-use IDs, and remaining-quantity replacement semantics.
- Integer tick representation, CSV replay, Hypothesis invariants, and CI.
- A research layer separated from matching; market-maker experiments already
  include multi-seed comparisons and P&L decomposition.
- **31 existing tests passed** locally before implementation.

## CLOB: gaps and resolution

| Finding | Resolution |
|---|---|
| Numeric validation accepted floats, infinities and booleans despite integer claims | Reject non-integer quantities/prices before state changes; add regression tests |
| Existing throughput included random generation and latency timers | Keep legacy entrypoint; add a separate prepared-stream benchmark |
| No p99, independent timing passes, repeated trials or native comparison | Four workloads, p50/p95/p99, five alternating trials, raw metadata/results |
| No measured profile to justify the rewrite | Prepared-stream cProfile and separate Python allocation pass |
| No native core | Independent C++17 core plus optional pybind11 adapter using existing Python value objects |
| Native correctness unproven | Reused regressions, randomized state parity, per-event output equality, boundary tests |
| README roadmap did not match the requested five stages | Explicit V1–V5 map, build/run instructions and linked measurements |
| Complexity notes treated heap size as active count and omitted depth sorting | Clarify stale entries, retained IDs and level sorting costs |

## Follow-up verification

All nine public READMEs were fetched again during continuation. Their content
hashes match the earlier review; [the source list](profile-readme-sources.json)
records the current README URLs and hashes. The initial file-inventory review is
retained; this refresh did not inspect every implementation or live deployment.

The original 77 tests passed again before continuation changes. The follow-up
closes a benchmark provenance gap: missing metadata previously allowed timing,
and metadata was not bound to the loaded binary. Validation now checks sources,
binary, Python ABI, checkout location and required metadata before timing.

It also adds min/max trial ranges, results from three input seeds in separate
processes, and structured profile metadata. See [the continuation report](CONTINUATION.md).

## Profile: highest-value changes

The [current profile README](https://github.com/asoracca/asoracca/blob/main/README.md)
already has an internship target, LinkedIn and a real email address. A cached
profile page showed an old email placeholder; the current README has fixed it.
Do not spend time fixing a stale cached issue.

1. **Feature the strongest engineering work first.** Put redline-exchange first,
   TradeGoons second, and the numerical-estimator work in soxl-vol-surface third.
   Follow with the poker solver and backtest-engine. Feature fewer projects with
   clear evidence rather than giving every market dashboard equal weight.
2. **Synchronize claims.** The profile says TradeGoons covers real trading, but
   its repository explicitly describes paper trading and no brokerage execution.
   Use “paper-trading journal and educational coach.”
3. Replace “showed the strategy has no alpha” with “the demo regression did not
   find statistically significant alpha.” The momentum README also explains that
   its fallback daily regression is distinct from the main monthly experiment.
4. Add school, major and expected graduation year **only with your actual details**.
   Retain the Summer 2027 target if still correct. Do not invent eligibility,
   coursework, users, revenues, or performance.
5. Give redline-exchange an About description such as “Deterministic Python/C++
   limit order book with differential tests, profiling and reproducible benchmarks.”
   Suggested topics: `order-book`, `matching-engine`, `cpp`, `python`,
   `market-microstructure`, `benchmarking`. Add a concrete About description to
   backtest-engine too. These metadata changes are recommendations, not applied.
6. For each pinned project, show a one-command demo, one visible result, its
   methodology/limitations, and tests. Keep CI badges linked to actual workflows;
   don't claim a green hosted run until it exists.

## Concrete repository recommendations

| Repository | Current evidence / next improvement |
|---|---|
| [tradejournal](https://github.com/asoracca/tradejournal) | Deployed app, architecture and environment setup are documented. README acknowledges no authentication or user isolation; no test/workflow paths appeared in inventory. Add authenticated user ownership with cross-user access tests, API validation tests, a seeded demo and a screenshot. Make “paper” consistent across repo/profile. |
| [soxl-vol-surface](https://github.com/asoracca/soxl-vol-surface) | Already has numerical-method tests and CI. Lead with estimator error/variance and Greeks validation; move the sprawling signal material below it. Present IV proxy assumptions alongside results, soften unsupported premium/edge assertions, and avoid treating a fixed trade-count threshold as proof of validity. `data/heston_smile.png` is referenced while generated data are described as ignored: put a stable example under assets and verify the rendered image. |
| [backtest-engine](https://github.com/asoracca/backtest-engine) | Clear next-open execution rule, ledgers, deterministic tests and CI. Add a small fully offline demo and link its expected ledger/equity output near the top. Highlight one timing regression and the long-only boundary in interview notes. |
| [pokeringdumdum](https://github.com/asoracca/pokeringdumdum) | Focused Kuhn CFR/CFR+ solver, exact exploitability, convergence figure, tests and CI. Add a short table of iteration budget, runtime and exploitability from a reproducible run. Use the subtitle “Kuhn Poker CFR Solver” in pins/resume if the playful name obscures its purpose. |
| [momentum-factor-backtest](https://github.com/asoracca/momentum-factor-backtest) | README now carefully separates development and holdout, corrects the bootstrap, and distinguishes the separate regression. Update the profile and repository description to match; the visible description still claims original-paper/“walk-forward” framing. Add a compact held-out result table with costs, dates, universe provenance and uncertainty. |
| [new-space-radar](https://github.com/asoracca/new-space-radar) | Figures and methods exist, but “Results So Far” still promises future results; inventory shows no tests or workflow. Add offline fixtures and tests for estimation-window exclusion, after-hours event alignment, overlapping events and signal timing. Publish event counts and a baseline comparison before expanding signal features. |
| [leveraged-etf-risk-lab](https://github.com/asoracca/leveraged-etf-risk-lab) | Several visible charts and a practical research question. The current README ends inside the Quickstart code fence. Close it and document outputs/testing. Add deterministic metric tests, a complete small synthetic portfolio fixture, and tests for missing histories/weights; inventory shows no test or workflow paths. |
| [asoracca](https://github.com/asoracca/asoracca) | Strong direction and contact links. Apply the claim corrections and project order above; feature redline/backtest/poker, which are currently missing from the featured-project prose despite being pinned. |

## Recruiting use

Be ready to explain one design decision, one bug, one test that caught a bug,
one measured result, and one limitation for each of your top three projects.
For Redline: explain maker pricing, replace priority, why canceled heap entries
can remain, why the C++ API includes Python overhead, and how exact parity was
checked. Describe what you personally verified and changed, including where AI
assisted. Do not present unreviewed generated code as expertise you cannot explain.

## Validation actually performed

- Baseline: 31 tests passed.
- Updated suite: 95 tests passed, including the native backend and 100 generated
  differential cases with state comparison after each operation.
- Native standalone core checks compiled and passed on this Mac.
- Ruff checks and formatting checks passed. Editable installation and original
  CLI/replay/benchmark smoke checks passed. A source copy without native binaries
  passed 41 tests with one expected native-module skip in the initial delivery;
  see the continuation report for the refreshed Python-only run.
- The published comparison uses 100,000 events per workload, seed 17 and five
  trials on local macOS arm64/Python 3.12.14, with exact parity checked first.
- Linux sanitizer and Python-version matrix jobs are configured; they have not
  been run on GitHub as part of this local task. Local standalone tests did not
  use sanitizers. No changes to other repositories or public profile were made.

Measured performance is in [the result table](performance/SUMMARY.md), with
[methodology](BENCHMARKS.md), [profiling findings](PROFILING.md), and the
[file-by-file change list](CHANGES.md).
