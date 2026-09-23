# Research Copilot: architecture, methods and operation

## Responsibilities and boundaries

The existing matching engine remains an independent package with no API, model
or persistence dependencies. `market_lab.py` remains unchanged. The new
`research_copilot` package wraps supported simulator settings and the existing
workload/parity helpers. No alternate C++ implementation was introduced.

| Component | Responsibility | Why |
|---|---|---|
| Planner | Live structured question interpretation; exact templates offline | A model is useful for mapping language to a finite simulator vocabulary. Offline mode does not claim this capability. |
| Runner | Deterministic schedule and closed registry | Scheduling, budgets, retries and arithmetic are more reliable as code. |
| Reviewer | Code checks sample size/intervals; optional separate model checks relevance | A valid numerical plan can still fail to address a question. The model can flag mismatch or uncertainty but cannot override code's uncertainty flags. |
| Reporter | Deterministic text renderer with evidence IDs | Models do not need to rewrite numerical claims. No free-form causal story or real-market claim is accepted. |
| Single-agent baseline | Same live research-agent role for planning and self-review | Same two decision points, context, tools and budgets. Separate reviewer role is the experimental difference; this is not a framework with autonomous conversations. |

The workflow is `draft → validated → running → reviewing → completed` with
`failed`, `canceled` and `interrupted` stops. Declines and clarification requests
are visible failed runs with a readable explanation and no simulations started.
Zero automatic plan revisions are used; a questionable study is returned as
inconclusive or question-mismatched rather than starting another search. A
completed run means its artifacts passed validation, not that its hypothesis
was supported.

## Controlled execution

Pydantic models forbid unknown fields and constrain settings, seed count,
scenario names, steps, treatment count and work estimates. A plan must contain
an exact estimate of `steps × seeds × configurations`. A benchmark has fixed
Python/C++ backends; arbitrary engines or functions cannot be supplied.

The registry exposes only `describe_simulator`, `validate_experiment`,
`run_simulation_batch`, `run_matching_benchmark`, `load_run_results`,
`compare_experiments`, `generate_chart`, and `save_research_report`.
Despite its name, a simulation batch tool executes one bounded scenario/seed
checkpoint; the runner owns iteration. Tool arguments include indices into the
validated schedule, not arbitrary Python or file paths. Every attempt is logged
with arguments, duration and success/error. Unsafe requests get no automatic retry.

Tool returns must match their scheduled task identity, configuration and exact
metric schema. Extra instruction fields, mismatched seeds, NaN and infinity are
rejected before persistence. Model review references must exist. Report claims
must cover each evidence ID exactly once and use the code-derived conclusion.
Imported arbitrary tools/notes are not supported. User text and model output are
rendered as text, never HTML or executable code. Artifacts use a fixed filename
allowlist inside SQLite. The API does not expose the registry directly.

Loopback binding, Host checking, same-origin writes and a 4 KiB POST limit bound
the local HTTP surface. This is not an authenticated multi-user server. Do not
expose it publicly without redesigning that boundary.

## Persistence, idempotency and recovery

SQLite schema version 1 is migrated in an explicit transaction. WAL and FULL
synchronous durability are enabled. A process file lock prevents two workers
opening the same store. An in-process lock guards the shared connection.
`runs` stores state/counters, `events` is an application-append-only action log,
`tasks` has unique `(run_id, task_key)`, `cache` has content keys, and `artifacts`
has fixed `(run_id, name)` slots. Saving a task and its cache entry is one explicit
transaction. Run metadata updates are separate atomic SQLite statements.

Work is reserved before execution. A crash between reservation and task commit
may charge a retry twice; it never silently refunds attempted work. A completed
checkpoint is skipped on resume. Progress is reconciled from task rows, and the
plan artifact is reconstructed from the immutable validated plan if needed.
Restart marks unfinished run records interrupted. A graceful shutdown requests
cancellation and waits for the current bounded operation to finish.

Cache keys include all validated plan settings, scenario/seed indices, source
content hashes, Python version, platform and the native binary hash when present.
Simulation tasks can be reused across runs. Timing tasks are not cached across
runs because timing depends on host conditions. Source/runtime changes prohibit
resuming an old run; start another experiment. Completed old reports remain readable.

Resume retains counters and active elapsed time; it does not grant a new budget.
At most three explicit resumes are allowed per run. Resource exhaustion generally
requires a new experiment with an appropriate bounded budget. Logs include failed
task arguments, so failures are not silently dropped from the research sample.
No report is completed while any scheduled task is missing.

`python scripts/research_recovery.py` temporarily substitutes a deliberate
fourth-task failure in its own process, restores execution, and resumes. It does
not add a failure endpoint to the app. [Measured output](research/recovery.json).
The restart test closes a store at a running checkpoint and reopens it through
a new Manager. The API test reopens the whole application and loads its old report.

## Limits and cancellation

| Resource | Default | Hard maximum |
|---|---:|---:|
| Logical work units | 40,000 | 100,000 |
| Tool calls including rejected attempts | 100 | 160 |
| Model attempts including transient retries | 4 | 6 |
| Reserved model output tokens | 6,000 | 12,000 |
| Active wall-clock seconds | 120 | 300 |
| Steps/events per task | 500 | 2,000 |
| Seeds per scenario | 6 | 12 |
| Treatments | 1 or 2 | 3 |
| Queued/running requests | — | 4 |
| Stored runs per directory | — | 100 |

Work counts simulation steps or timed benchmark events, including cached tasks
and failed attempts. Benchmark generation/parity replay adds bounded overhead
outside those logical units. The wall budget is checked around each operation;
it is cooperative, not an operating-system CPU kill. Cancellation waits for the
current simulation or provider request; it cannot stop a C++ call midway. HTTP
calls use an at-most-30-second transport timeout, bounded by remaining active
budget. Queue time is excluded from active elapsed time. A hard process kill can
lose the elapsed fraction since the last checkpoint. These limits are for local
resource control, not a security sandbox for untrusted Python plugins.

## Statistical method

All simulation groups start at fair value 10,000 ticks. Baseline seed schedule is
17, 42, 73, 101, 137, 211; treatment index i adds `100000 × i` to every seed. This
uses distinct reproducible streams. **No common-random-number benefit is claimed.**
Changing informed share changes random-number consumption in the existing
simulator, so identical seed labels alone would not establish exogenous alignment.

Per group: n, arithmetic mean, sample standard deviation (`ddof=1`), and an
exploratory normal interval `mean ± 1.96 × SD / sqrt(n)`. For treatment minus
baseline: `delta ± 1.96 × sqrt(SD_t²/n_t + SD_b²/n_b)`. No multiplicity correction.
With fewer than five seeds, every directional claim is forced inconclusive.
Otherwise an interval crossing zero is inconclusive. These small-sample normal
intervals can under-cover; they are not confirmatory inference. No strong
best-configuration ranking is emitted, including in the tradeoff example.
Positive/negative denote the signed difference, not whether a metric improved.

| Metric | Meaning and unit |
|---|---|
| Ending P&L | Final cash plus inventory marked at final synthetic fair value; tick × quantity |
| Maximum absolute inventory | Largest absolute position at a recorded step; quantity |
| Maximum drawdown | Largest running-peak minus current marked P&L, starting peak at zero; tick × quantity |
| Execution edge P&L | Sum of maker execution edge against contemporaneous fair value, weighted by filled quantity; tick × quantity |
| Inventory revaluation P&L | Ending P&L minus execution edge; tick × quantity |
| Core API ns/event | Timed prepared workload replay divided by event count; nanoseconds, includes Python/binding overhead |

Quote refresh interval is **simulation steps**, not a measured network delay.
Noise/informed traders and inventory rules are simplified. There are no fees,
rebates, empirical calibration, options or historical/live feeds. There is no
claim of real profitability, causal market behavior or optimal trading policy.

The C++ example generates the same workload for each backend/seed, verifies
responses and final state outside timing, and times existing API replay with
history retention disabled. It runs one short trial per seed and does not
alternate backend order. Its unpaired intervals do not remove thermal/order
noise. Use the original five-trial alternating study for a more substantial
comparison; none measures distributed exchange capacity.

## Evidence and reproducibility

Each completed run contains `plan.json`, `results.json`, `results.csv`,
`comparison.json`, `chart-inputs.json`, `chart.svg`, `review.json`, `report.md`,
`logs.json` and `evidence.json`. The manifest hashes all other artifacts and
records source files, runtime, plan, mode and supplied usage. The final completed
state event follows the evidence checkpoint; the frozen log artifact covers
all validation work through that checkpoint. Later UI reads do not alter artifacts.

Plan, numerical tables, comparison, chart and report are deterministic for the
same offline plan/source/runtime. Timings, run IDs, log timestamps, manifests
containing timing, and C++ timing results are deliberately not byte-identical.
Tests compare the deterministic subset and recompute report values from seed rows.
[Saved report](research/example/report.md) · [Evidence manifest](research/example/evidence.json).

## Live provider

`OPENAI_API_KEY` and `OPENAI_MODEL` are environment-only. `.env.example` is a
reference template, not a dotenv loader. The adapter uses the fixed OpenAI
Responses endpoint with `store=false`, strict JSON Schema, closed properties,
all fields required, and a per-attempt output-token reservation. It sends no
provider tools and grants no shell, network destination selection, source edits
or brokerage access. Request questions/plans and review evidence are sent to
the provider in live mode; offline mode makes no provider requests.

Only network errors, timeout, HTTP 429 and HTTP 5xx get one retry. Invalid schema,
refusal, incomplete output and other HTTP errors stop immediately. Output-token
reservations are conservative and persist even if an attempt fails. Input is
bounded by schemas and fixed context rather than an exact tokenizer quota.
Usage counters include only provider-supplied integer counts; failed requests
may have unreported usage. Monetary cost is always unavailable because there is
no documented per-model pricing configuration. Do not read unavailable as zero.
Raw authorization headers and provider response bodies are not logged. Known key
values and credential-like strings are redacted in run metadata/action logs.

The adapter follows the official [Structured Outputs guide](https://developers.openai.com/api/docs/guides/structured-outputs)
and [Responses reference](https://developers.openai.com/api/reference/resources/responses/methods/create).
Framework usage follows [Python 3.12 SQLite](https://docs.python.org/3.12/library/sqlite3.html),
[React effect cleanup](https://react.dev/reference/react/useEffect), and
[Vite 7 multiple entry points](https://v7.vite.dev/guide/build.html#multi-page-app).
Installed/tested versions are recorded below; no dependency upgrades were needed.

**Live integration is unverified here.** Mocked tests cover request shape,
usage, redaction, transient retry, refusal/incomplete/invalid outputs and fake
review citations. To run the opt-in comparative evaluation after configuring a
compatible account-accessible model:

```bash
python -m research_copilot.evaluate_live --output live-evaluation
```

This command makes billable provider calls. It runs 14 prompt cases per workflow,
records actual outcomes/usage in SQLite and JSON, and explicitly marks the two
statistical-fixture rows not run as live prompts. Use fresh output directories
for independent repetitions. Numerical evidence validation does not prove
semantic question/plan relevance; human assessment is still required.

## API and UI

`GET /api/research/capabilities` returns supported controls and tool schemas.
`POST /api/research/runs` accepts `question`, `mode`, `workflow` and bounded
`limits`. `GET /api/research/runs` returns history; `GET .../runs/{id}` returns
state, plan, counters, ordered action records and artifact names.
`POST .../runs/{id}/cancel` and `.../resume` operate only on that run.
`GET .../runs/{id}/artifacts/{fixed-name}` reads an artifact. Invalid paths are
not resolved against the filesystem. Errors use 404/409/422/429 where applicable.
OpenAPI is available at `/docs` on the local service.

The React app polls durable snapshots every 700 ms. It displays action summaries,
not hidden reasoning. Refresh/restart recovery uses the history list; selecting
an old run reloads saved evidence. The exchange demo remains a separate process
at port 8000; the research app is at 8001. Both use the same built frontend assets
but separate APIs/databases. Browser tests run an isolated server at 8002.

## Validation record

Baseline revision: `5dd9a922f61b1b8b812eba3a141ec79a4cd0e906`; 103 baseline tests.
Local implementation validation on 2026-09-23: Python 3.12.14, Pydantic 2.13.5,
FastAPI 0.141.1, Starlette 1.6.0, httpx 0.28.1, Uvicorn 0.53.0, React 19.2.0,
TypeScript 5.9.3, Vite 7.3.6, Playwright 1.63.0. No engine source changed.

- 131 Python tests passed, including native parity and 28 new research tests.
- Ruff checks and formatting passed; TypeScript check and production build passed.
- Research browser test exercises real submit/results, numerical report, chart,
  plan, logs, artifact links, history reload, budget failure and 390px layout.
- Exchange browser regression exercises submit/fill/cancel/replace/reset/replay.
- Offline evaluation: 32 measured rows (16 per workflow), all expected outcomes;
  [method, timings and raw results](research/evaluation/RESULTS.md).
- Recovery script reproduces failed/resumed task counts; native research benchmark
  verifies parity; original full three-seed core study was rerun unchanged.
- Two existing upstream Starlette/httpx/AnyIO deprecation warnings remain.
- Live provider requests and live comparative rows: **not run**. CI configuration
  was extended locally; remote CI has not run because this work has not been pushed.

Core API timings are in [the rerun study](research/core-study/STUDY.md), which
records source hashes, Python/compiler/OS metadata, all trials and seeds. Whole
research workflow latency includes SQLite, simulation, validation and rendering;
it is in the offline evaluation. Browser click-to-visible latency is separately
recorded in [browser sample](research/ui-latency.json). It includes polling and
local service time; one observation is not a latency distribution. These three
measurements answer different questions and are not compared as throughput.
