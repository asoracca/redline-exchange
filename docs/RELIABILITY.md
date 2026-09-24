# Bounded research workflow and evaluation

The product executes `question → structured plan → validation → simulation →
computed evidence → review → certified report`. Numerical calculations and report
wording come from Python. The model can select a supported plan and assess relevance;
it cannot change metrics, execute arbitrary tools, write files, or declare success.

## What has actually been exercised

| Component | Implemented | Evidence and limits |
|---|---|---|
| Scripted planner/reviewer | Six exact templates and deterministic review | Real local simulations, HTTP and browser tests; no language-model inference |
| Responses adapter | Fixed endpoint, strict output schema, no tools, bounded transient retries | Mocked HTTP tests only; **live model behavior unmeasured** |
| Orchestrator | Single worker, four-run queue, work/tool/model/output/time budgets, cancel/resume | Real task execution, fault injection and restart/checkpoint tests |
| Numerical reporting | Seed records, means, sample SD, exploratory intervals, evidence IDs and artifact hashes | Recomputed evaluation checks and adversarial evidence tests; not scientific validation of the simulator |
| SQLite | WAL/FULL, process lease, transactional task/cache checkpoint and state/event transitions | Transaction rollback and reopen tests; single-process POSIX scope |
| C++17 | Existing core behind Python value-object adapter | Original parity/property tests and repeated API study; no new matching implementation |
| React/TypeScript | Generated request/response contracts, progress, parameter changes, uncertainty, failure/recovery views | Real browser flows plus explicitly mocked gateway/artifact failures |

Malformed JSON/envelopes, schema violations, refusals and incomplete responses fail
without semantic retries. Network/transport errors, HTTP 429 and 5xx get at most
one retry, with a short cancellation-aware backoff. Every attempt reserves model
and output-token budgets. Usage is marked incomplete if an attempt supplies no
usable token counts. Unknown usage is never presented as total zero cost.

Responses are streamed into a 256 KB cap. Cancellation and total elapsed budget
are checked between chunks and between tasks. HTTPX timeouts govern network
inactivity, not a hard total deadline. A blocked request may wait for its current
transport timeout; a simulation may finish its current bounded batch. This is
cooperative cancellation, not a hard real-time guarantee.

A contradictory planning decision is rejected. The plan becomes immutable after
validation. A reviewer citing a missing evidence ID stops the run. A reviewer
flagging question mismatch retains the plan, results and review for inspection,
but does not certify a report. Neither live review nor prompt text can promote an
uncertain numerical comparison into a strong claim. This is a bounded data flow,
not proof of general prompt-injection resistance by a model.

Task and cache writes commit together. Resume skips completed tasks, keeps original
budgets, and invalidates earlier report/review certification. Failed attempts remain
charged. Source/runtime changes prevent resume. Question rejection, question mismatch
and exhausted budgets require a revised new experiment, which the UI now explains.
A hard process kill can lose elapsed time since the last persisted check. Provider
attempts are reserved before calls, but a lost response can leave token usage unknown.

## Evaluation v2

[Dataset](../evaluations/research-v2.json) · [freeze record](../evaluations/research-v2.lock.json) ·
[scorecard](research/evaluation-v2/RESULTS.md) · [raw rows](research/evaluation-v2/results.json)

There are 24 question cases: 12 development and 12 held-out, with five supported
and seven clarification/rejection cases per split. The exact held-out wording is
absent from the scripted lookup and provider examples. The dataset was authored
locally and visible during implementation; it is **not an independently blinded
benchmark**. Its file hash was frozen before the first held-out scoring run.
Do not tune v2 against the published held-out failures; use a new version.

Each case gets a fresh store and identical limits in either mode: 12,000 work
units, 40 tools, four model attempts, 6,000 reserved output tokens and 60 active
seconds. Scripted and live both use the staged workflow. The optional single-role
setting remains available, but this experiment does not test a multi-agent benefit.

| Metric | Development scripted | Held-out scripted | Live |
|---|---:|---:|---|
| Expected outcome | 12/12 | 5/12 | Unmeasured |
| Supported task completion | 5/5 | 0/5 | Unmeasured |
| Valid plan on supported cases | 5/5 | 0/5 | Unmeasured |
| Plan matches control/metric oracle | 5/5 | 0/5 | Unmeasured |
| Evidence correct among completed studies | 5/5 | 0/0, not eligible | Unmeasured |
| Appropriate clarification/rejection | 7/7 | 5/7 | Unmeasured |

The expected-outcome Wilson 95% intervals are **[75.75%, 100%]** and
**[19.33%, 68.05%]**. These describe this small authored suite, not general model
performance. Raw JSON provides every metric's numerator, denominator and interval,
latency sample, usage coverage and failure example. A failed policy expectation is
an evaluation result, not necessarily a software exception. Quality failures do not
make the measurement CLI discard its output or hide cases.

The baseline correctly declines unsupported/injected requests but cannot handle the
five held-out supported paraphrases; it also declines two ambiguous questions instead
of asking for clarification. No held-out failure was added to the template lookup.
The deterministic plan oracle checks expected baseline controls, treatment controls
and metrics. Full semantic/scientific relevance still needs human review.

Evidence checks reconstruct comparisons from validated task records, regenerate the
exact deterministic report, and check artifact hashes. They measure arithmetic and
reference integrity, not language-model truthfulness. Insufficient-sample, fabricated
citation, malformed-output and recovery scenarios are software tests, kept out of the
question-quality denominators. Historical [v1 results](research/evaluation/RESULTS.md)
remain available and must not be cited as live-model evidence.

Reproduce without credentials, in a fresh output directory:

```bash
python -m research_copilot.evaluate_v2 --split development --output /tmp/redline-dev-v2
python -m research_copilot.evaluate_v2 --split held_out --output /tmp/redline-held-v2
```

Live evaluation has **not been run**. After separately authorizing credentials and
spending, configure `OPENAI_API_KEY` and `OPENAI_MODEL`, verify that model's current
input/output prices, then supply all of these flags (replace the placeholders):

```text
python -m research_copilot.evaluate_v2 --split all --output live-evaluation/run-001 \
  --authorize-live --budget-usd <AUTHORIZED_BUDGET> \
  --input-usd-per-million <VERIFIED_INPUT_PRICE> \
  --output-usd-per-million <VERIFIED_OUTPUT_PRICE>
```

Credentials alone never trigger evaluation calls. Each attempt reserves a conservative
amount before sending: serialized UTF-8 request bytes plus a 4,096-token framing
allowance, and the full output cap, priced at the supplied rates. Reservations are
persisted and never refunded, including retries or missing usage. Exhausted budget
prevents the next request. This local estimate is **not a provider-side hard dollar
cap or invoice**; it assumes the supplied rates and token allowance are conservative.
Use account-side controls where available. Costs remain unavailable in the app;
provider-reported token totals include coverage flags. Fresh output directories prevent
silent result/ledger replacement. Completed evaluation rows survive evaluator interruption.

## Reproducible demonstration

After the README's one-time setup, `python copilot.py` starts the app. If port 8001
is already occupied, use `python copilot.py --port 8005` and open that port.

1. Select **Quote latency**, run the experiment, and open **Plan**. Inspect the
   change from refresh interval 1 to 5 and six seeds per group.
2. Inspect **Findings**: ending P&L difference is −3,186.67 tick × quantity with
   exploratory interval [−5,565.69, −807.65]. Follow its evidence and raw seed records.
   Other metrics can remain inconclusive; this is an artificial model, not trading advice.
3. Open **Activity & usage**: the offline run made zero model calls. Then enter
   an unsupported question locally: the explanation appears and no report is certified.
4. Set the work limit to 40 and rerun an example. It fails before simulation;
   the UI tells you to revise the budget, rather than offering an ineffective resume.
5. Run `python scripts/research_recovery.py`: three completed checkpoints survive
   a deliberate fourth-task failure; resume finishes 12 unique tasks at 6,500 charged
   work units. [Recorded result](research/recovery-v2.json).

The screenshot in the README is taken from the running app by the browser suite.
Public hosting retains its restricted, scripted example mode; these local changes
must be explicitly published to update that deployment.

## Timing boundaries

[Core raw study](research/core-study-v2/STUDY.md) uses unchanged benchmark code:
100,000 events/workload, four workloads, seeds 17/42/73, five trials/backend/seed
(120 trials). Generation, construction and exact parity verification precede timing;
C++ measurements include pybind11 and conversion to the same Python objects.
All trials are retained. Median C++/Python throughput ratios are **1.28×–2.52×**.
The cancel/replace trace intentionally does not vary across seeds. This active
laptop was not isolated from background work; brief local test activity occurred
during the study. No performance improvement over the previous code is claimed.

[Separate local service samples](research/service-timing-v2.json) record 200 tiny
SQLite task/cache commits (median 0.146 ms), 20 warmed empty-history loopback HTTP
GETs (median 0.765 ms), and three full quote-latency workflows (124.53 ms cold,
55.98/55.04 ms with 12 cache hits). These are unlike workloads; do not subtract
numbers to infer overhead. Browser click-to-visible sampling is recorded separately
in [ui-latency-v2.json](research/ui-latency-v2.json), including polling and rendering.
One browser observation is not a latency distribution or an SLA.

```bash
python -m pytest tests/test_native.py tests/test_validation.py -q
python study.py --orders 100000 --repeats 5 --seeds 17 42 73 --output /tmp/redline-core-v2
python scripts/measure_research_service.py --output /tmp/redline-service-v2.json
pnpm --dir web run test:research
```

Official references checked for this work: [Responses structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs),
[HTTPX timeout semantics](https://www.python-httpx.org/advanced/timeouts/),
[Python 3.12 SQLite transactions](https://docs.python.org/3.12/library/sqlite3.html),
and [React effect cleanup](https://react.dev/reference/react/useEffect).

## Validation record for this revision

Application commit: `e85462e` (subsequent documentation/evidence commit does not
change the measured implementation). Local Python 3.12.14 validation passed
**158 tests**, Ruff lint/format checks, generated contract checks, TypeScript
checking and the production build. Five research browser scenarios and three
original exchange scenarios passed. Two research scenarios deliberately mock
HTTP failures; the others use running local services. The new dedicated browser
output directory preserves research artifacts when exchange tests run afterward.
Two pre-existing Starlette/httpx/AnyIO deprecation warnings remain.

Remote CI has not run on this local branch. The existing Docker build/deployment
was not rerun for these changes. No live provider request or paid evaluation was
made, and the published Render app was not changed.
