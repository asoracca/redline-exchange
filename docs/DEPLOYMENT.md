# Free public demo deployment

[Open the public demo](https://redline-research-copilot.onrender.com/).
On September 23, 2026, the Render Free service passed its health check and
browser verification with application commit `f469bb8`. Quote latency completed
12 tasks and reproduced the documented −3,186.67 tick × quantity difference.
The Python/C++ example also completed all 12 tasks; its shared-host timing
comparison was inconclusive. These checks establish functionality, not capacity
or representative benchmark performance.

The repository includes a Render Blueprint (`render.yaml`) and a Docker image
for the real Python service and built React frontend. The image compiles the
existing C++17 extension, so the small Python/C++ benchmark is available too.
No paid AI, disk, database, custom domain or paid service is configured.

A Render account is required. In the dashboard, create a Blueprint from
`https://github.com/asoracca/redline-exchange`, select branch
`codex/research-copilot`, and use `render.yaml`. Confirm that the service plan is
**Free**. Automatic redeployment is disabled; publish tested versions explicitly.
Do not switch to a paid plan or add a persistent disk for this free demonstration.

The Blueprint uses `/healthz`, one process, and the platform's `PORT`.
`RENDER_EXTERNAL_HOSTNAME` supplies the exact allowed host. The image runs as a
non-root user. `deploy.py` refuses to run without `REDLINE_PUBLIC_DEMO=1`.
Docker build and real simulation/native smoke checks run in CI. Local Python
and browser tests also exercise the restricted public mode.

## Public versus local behavior

Public mode accepts only the six example questions and forces scripted offline
planning. The text area is read-only; visitors select examples. Live requests
are rejected at the server even if a provider key is accidentally configured.
Arbitrary questions are rejected before any run is persisted. Public mode refuses
to open a store containing local/private runs.

Runs and evidence are **shared publicly** and labeled accordingly. This is a
synthetic example gallery that executes real research tasks, not a private
workspace. Visitors cannot cancel or resume another visitor's run. They can
start another example. Request rate is six per minute globally; the single
worker has at most four pending/running jobs. Each run has at most 9,000 logical
work units, 40 tool calls and 30 active seconds. These are demo bounds, not a
claim of protection against a determined denial-of-service attack.

Only the latest 50 runs are retained. Older terminal public runs and their
artifacts are evicted transactionally. Active jobs are protected from eviction.
The local app keeps its original history and cancellation/resume behavior.
The public container uses its own `/tmp/redline-public` directory; never point
it at a private/local research database.

Render's free web services sleep after 15 idle minutes, so the first visit may
be slow. The filesystem is ephemeral: restarts or redeploys can lose saved runs.
Download evidence you want to keep. Account-level free usage limits also apply.
See [Render free-service limits](https://render.com/docs/free),
[Docker hosting](https://render.com/docs/docker), and
[Blueprint reference](https://render.com/docs/blueprint-spec).

## Local container check

With Docker installed:

```bash
docker build -t redline-public .
docker run --rm -p 127.0.0.1:8010:10000 \
  -e REDLINE_PUBLIC_DEMO=1 \
  -e REDLINE_PUBLIC_HOST=127.0.0.1 \
  -e REDLINE_RESEARCH_DIR=/tmp/redline-public redline-public
```

Open http://127.0.0.1:8010. No API key is needed. Deployment still requires a
successful platform build and health check; committed configuration alone does
not mean the site is live.
