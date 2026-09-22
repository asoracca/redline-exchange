# Local exchange laboratory

The default and only input mode is **synthetic simulation**. AAPL, MSFT, NVDA
and DEMO identify independent in-memory books; none is a quote feed. No provider,
brokerage credentials, outbound data requests or brokerage order path exists.
A future provider adapter must be separately labeled historical or live, read-only,
and kept outside the synthetic order entry path.

## Architecture

React/TypeScript → typed FastAPI commands → serialized Python exchange → existing
Python reference book or C++17/pybind11 adapter. SQLite records the command and
its accepted/rejected result in one explicit transaction. HTTP handlers contain
no matching logic. The TypeScript contract is generated from server OpenAPI.

A single reentrant lock covers every state mutation, SQLite transaction, and
snapshot. This deliberately serializes all books, a stronger restriction than
one writer per book. Each committed event gets one session-global sequence,
which defines concurrent request order (not client send timestamps). Symbol
books never share matching state. The native boundary holds the GIL and converts
C++ results to the existing Python value objects; it does not implement HTTP or SQL.

PR #3 was reviewed as a draft proposing a different C++20 core. This service uses
the existing main-branch C++17 adapter and changes neither matching implementation.
See [native contract](NATIVE.md) for details and the original parity methodology.

## Contract

- One tick = $0.01; quantity = whole synthetic shares. Command price and quantity
  are strict integers in 1..1,000,000. Booleans, floats, numeric strings, extra
  fields, unsupported symbols and malformed IDs fail validation (HTTP 422).
- Request and order IDs use 1–64 ASCII letters, digits, underscores or hyphens.
- Order IDs are single-use within `(session, symbol, epoch)`, including filled,
  canceled and unfilled market orders. The same ID can exist on another symbol.
- RESET starts a fresh book epoch for its symbol. It does not delete the journal,
  reset the global sequence, or free request IDs. Other symbols are untouched.
- Better price first, then order arrival sequence. Execution uses the maker price.
  Market remainders are discarded; limit remainders rest.
- Cancel requires an active order. Replace quantity is new **remaining** shares.
  Same-price reductions/equal quantity keep priority; increases or repricing
  lose priority and can immediately trade. Use cancel instead of zero quantity.
- Engine order/trade sequences restart on RESET; they are distinct from the
  monotonically increasing journal cursor. Interpret them with symbol and epoch.

`POST /api/commands` accepts the discriminated LIMIT/MARKET/CANCEL/REPLACE/RESET
union. `GET /api/snapshot` returns all books at one cursor, depth (top 20 levels),
active orders and current-epoch trade history. `GET /openapi.json` documents typed
requests and responses. The UI displays the most recent 20 fills.

Structurally valid commands that violate book rules (duplicate ID, missing active
order) are journaled with `accepted:false`, no trades and an error. These return
HTTP 200 because the envelope itself was processed. Validation errors (422),
idempotency conflicts (409), resource limits (429), and origin failures (403)
are transport rejections; they do not allocate a journal sequence.

Request IDs are unique across the entire database session, including RESETs and
rejected business commands. An identical retry returns the original event without
applying it again. Reusing the key with different normalized contents returns 409.
The browser keeps the same request ID for explicit retries after network failures.

## Persistence and recovery

Migration `src/exchange/migrations/001.sql` creates the journal and sets SQLite
`user_version=1`. Unsupported versions fail closed. SQL triggers disallow UPDATE
and DELETE on journal rows. Writes use BEGIN IMMEDIATE / COMMIT with synchronous
FULL. No log compaction or production database is involved.

Matching occurs while the transaction and writer lock are held. No observer sees
the tentative result. A failed insert/commit rolls back and rebuilds all books
from committed events, then propagates the failure. A crash before commit leaves
no event; a crash after commit is resolved by retrying the same request ID. On
startup, replay re-executes commands and checks every saved accepted/rejected
result and every trade. Unknown schema or replay disagreement prevents startup.
Keep the same engine/backend version for a saved journal; error text is part of
the checked result and can differ between backend versions.

`GET /api/replay` reconstructs fresh books, checks every event, then compares final
state and trades with the current service. `?through=N` reconstructs a prefix
without mutating the current books. The UI captures an end cursor and supports
play, pause and single-step inspection of those saved events. Reading a prefix
verifies event results; full replay also verifies final state.

## Ordered stream

`GET /api/events?cursor=N` sends committed `exchange` SSE frames after N, followed
by a coherent `snapshot` frame. Every data frame includes an `id` cursor;
Last-Event-ID overrides the query cursor on reconnect. Snapshots can share the
preceding event's ID. Consumers deduplicate exchange events by sequence and replace
view state on a snapshot. No event is published before commit. The polling loop
checks SQLite every 250 ms and sends keepalive comments while idle.

Cursors belong to one database session, whose ID appears in snapshots. On initial
connection or uncertain session identity, fetch a fresh snapshot, then connect
from its cursor. Out-of-range cursors return 409 and require a new snapshot.
The browser follows that snapshot-first procedure on reconnect. The raw stream
also supports replaying missed events directly, tested with Last-Event-ID.

## Local bounds and limitations

Use `python demo.py`: loopback only, one process, at most 32 concurrent connections
and eight SSE streams. A POSIX advisory file lock refuses a second process on the
same database. Supported local platforms are macOS/Linux/WSL. No authentication,
distributed writers, deployment, or network capacity claim is intended.

The journal stops at 2,000 events, including RESETs and rejected book operations.
Start with a different `REDLINE_DB` filename for a new session; existing sessions
remain replayable. Four symbols, bounded IDs and numeric inputs limit demo growth,
including seen IDs, stale heap entries and trade history. Large snapshots and
prefix replay still take linear work; this is intentionally a short-session lab.
POST bodies above 4 KiB are rejected. Only same-origin browser writes are allowed.
Use it as a trusted local demo, not a hostile-network service.

## Two-minute walkthrough

1. **0:00–0:20** Open the demo and point out “Synthetic simulation.” Select DEMO.
   Press Single step three times: reset, then a seller at $101.05 followed by a
   cheaper seller at $101.00. The cheaper seller appears at the top despite
   arriving later.
2. **0:20–0:45** Step once: buy 130. The fills are **100 at $101.00 and 30 at
   $101.05**. The expensive seller has 70 remaining.
3. **0:45–1:05** Step twice: add a later seller at $101.05, then buy 80. The older
   seller fills 70 before the later seller fills 10. Explain price-time priority.
4. **1:05–1:20** Step twice: MSFT receives a $200 bid. Switch between MSFT and
   DEMO: the bid never crosses the other symbol's $101.05 ask.
5. **1:20–2:00** Click Replay saved session. The service verifies final state and
   trades. Play, pause, or single-step through the saved journal, then Return to
   current book. Use order entry and cancel/replace to explore further.

![Running synthetic laboratory](assets/exchange-lab.png)

## Validation and timing

```bash
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python scripts/export_contracts.py
cd web
pnpm exec openapi-typescript openapi.json -o src/contracts.d.ts
pnpm run build
pnpm exec playwright install chromium
pnpm test
```

The browser suite covers the lesson, manual submission/fill/replace/cancel/reset,
saved replay, cursor reconnect, and a narrow viewport. CI retains the original
engine/native jobs and adds the demo build and Chromium tests. Configured CI is
not evidence of a hosted run.

`python scripts/measure_service.py --events 200` measures two distinct layers on
an identical deterministic resting stream, no random seed: core API calls and
service calls including SQLite commit, excluding HTTP. Raw versions and samples
are summarized in [service-timing.json](service-timing.json). On this local run,
Python p50 was 1.417 µs core versus 346.896 µs service; C++ was 0.709 µs versus
351.958 µs. These are one short pass, no warmup, no repeated-trial inference.
The passing local Chromium run measured 60 ms click-to-visible-fill latency for
one 40-share fill (Playwright 1.63.0, Chromium 153.0.8010.12,
React 19.2.0, Vite 7.3.6; `CI=true pnpm --dir web test`). Browser tests separately print that latency, which includes
browser scheduling, HTTP, persistence and rendering. The UI's command+refresh
metric stops before React paint and is labeled accordingly.

The existing matching and benchmark code is unchanged, so the existing
[three-seed core study](performance/STUDY.md) remains the relevant larger study.
Neither it nor these local measurements establish exchange capacity: networking,
risk controls, replication and production operations are absent.

Implementation references: [FastAPI request models](https://fastapi.tiangolo.com/tutorial/body/),
[Pydantic strict fields](https://docs.pydantic.dev/latest/concepts/strict_mode/),
[React effects](https://react.dev/reference/react/useEffect), and
[SQLite transactions](https://www.sqlite.org/lang_transaction.html).
