# Research evaluation v2

Scripted and live use identical cases, limits and tools; each case starts cold. Live rows marked unmeasured are not failures and have no estimated model-quality score.

| Mode / split | Expected outcome | Completion | Valid plan | Plan relevance oracle | Evidence | Appropriate rejection |
|---|---|---|---|---|---|---|
| offline/development | 12/12 | 5/5 | 5/5 | 5/5 | 5/5 | 7/7 |
| offline/held_out | 5/12 | 0/5 | 0/5 | 0/5 | unmeasured / no eligible cases | 5/7 |
| live/development | unmeasured / no eligible cases | unmeasured / no eligible cases | unmeasured / no eligible cases | unmeasured / no eligible cases | unmeasured / no eligible cases | unmeasured / no eligible cases |
| live/held_out | unmeasured / no eligible cases | unmeasured / no eligible cases | unmeasured / no eligible cases | unmeasured / no eligible cases | unmeasured / no eligible cases | unmeasured / no eligible cases |

Raw JSON includes Wilson 95% intervals, all denominators, median/p95 latency, usage coverage and failure examples. These intervals describe a small authored suite, not a random sample of all user questions. Evidence correctness is conditional on completed runs; it measures deterministic arithmetic/references, not model truthfulness. The plan oracle checks declared controls/metrics, not full scientific relevance. Latency includes orchestration, simulation, provider waits (if live) and SQLite, excluding HTTP/browser. No live quality or multi-agent superiority follows from mock tests.

Development cases may guide changes. Held-out wording is excluded from planner templates and prompts. Locally authored and visible to the implementer, not an independently blinded test. Freeze the file hash before scoring; never tune against held-out failures in this version.

Held-out paraphrases are intentionally absent from the scripted template lookup. Do not broaden that lookup to erase measured failures; use a new dataset version for further tuning.

## Failure examples
- offline/held_out: What happens to ending P&L and inventory if quotes refresh every five simulation steps rather than every step? Expected completed; got unsupported.
- offline/held_out: In a market with informed share 0.7, compare an inventory cap of 20 with the default cap of 100. Measure ending P&L. Expected completed; got unsupported.
- offline/held_out: Compare the default market maker with an inventory cap of 20 and, separately, a half-spread of six ticks. Report P&L and maximum drawdown without declaring an unqualified winner. Expected completed; got unsupported.
- offline/held_out: Raise fair-value volatility from four to ten ticks. Compare execution-edge P&L across synthetic runs. Expected completed; got unsupported.
- offline/held_out: Compare ending P&L with half-spreads of three and six ticks in the artificial market. Expected completed; got unsupported.
- offline/held_out: Can you optimize this setup for me? Expected clarify; got unsupported.
- offline/held_out: Which setting should I choose? Expected clarify; got unsupported.
