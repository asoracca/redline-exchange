# Offline evaluation — dataset v1

These are scripted planning and deterministic software checks, not evidence of model quality. Both workflows use the same tools, budgets, questions and code guards. The staged live workflow uses a separate reviewer role; the baseline uses one research-agent role for both calls, with the same question/plan/evidence context. Offline both intentionally execute the same script. No multi-agent advantage is demonstrated.

| Workflow | Assertions | Supported completion | Invalid tool calls | Unsupported numerical claims | Total seconds | Tokens / cost |
|---|---:|---:|---:|---:|---:|---|
| staged | 16/16 | 5/5 | 0 | 0 | 0.6615 | unavailable |
| single_agent | 16/16 | 5/5 | 0 | 0 | 0.6633 | unavailable |

Latency includes planning, validation, simulation, SQLite and report generation in one local process, excluding browser/network. Sequential cold stores; one pass, not a latency significance test. Five supported studies per workflow, six seeds each (17,42,73,101,137,211), 500 steps; tradeoff has three groups, others two. Reject cases are successful policy outcomes, not completed studies. Insufficient-evidence rows use controlled statistical fixtures. Invalid calls count attempted rejected registry calls; separate adversarial unit tests deliberately exercise rejection. Unsupported claim count checks required evidence IDs and rendered numerical deltas, not natural-language model quality. See raw rows for all timings.

Live staged: **not run**. Live single-agent baseline: **not run**. No live completion, latency, token or cost claims.

Reproduce from the repository root:

```bash
python -m research_copilot.evaluate --output docs/research/evaluation
python -m pytest tests/research -q
```
