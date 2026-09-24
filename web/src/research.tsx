import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./research.css";

import type { components } from "./research-contracts";
type Summary = components["schemas"]["RunSummary"];
type Run = components["schemas"]["RunView"];
type Capabilities = components["schemas"]["Capabilities"];
type Stats = { mean: number; sd: number; n: number; low: number; high: number };
type Comparison = {
  groups: Record<string, Record<string, Stats>>;
  method: string;
  seed_schedule: string;
};
const BASE = "/api/research";
async function request<T>(
  path: string,
  method = "GET",
  body?: unknown,
): Promise<T> {
  const r = await fetch(BASE + path, {
    signal: AbortSignal.timeout(15000),
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!r.ok) {
    const e = await r.json().catch(() => ({
      detail: `Server returned HTTP ${r.status}. Try again when the service is available.`,
    }));
    throw Error(
      typeof e.detail === "string" ? e.detail : "Request validation failed",
    );
  }
  return r.json();
}
async function fetchArtifact(url: string): Promise<Response> {
  const response = await fetch(url, { signal: AbortSignal.timeout(15000) });
  if (!response.ok)
    throw Error(
      `Artifact unavailable (HTTP ${response.status}). Reload this run to retry.`,
    );
  return response;
}
const fmt = (n: number) =>
  n.toLocaleString(undefined, { maximumFractionDigits: 2 });
function App() {
  const [examples, setExamples] = useState<string[]>([]),
    [question, setQuestion] = useState(""),
    [history, setHistory] = useState<Summary[]>([]),
    [selected, setSelected] = useState<string | null>(null),
    [run, setRun] = useState<Run | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [mode, setMode] = useState("offline"),
    [workflow, setWorkflow] = useState("staged"),
    [live, setLive] = useState(false),
    [publicDemo, setPublicDemo] = useState(false),
    [comparison, setComparison] = useState<Comparison | null>(null),
    [report, setReport] = useState(""),
    [tab, setTab] = useState("Findings"),
    [budget, setBudget] = useState(40000),
    [pollRevision, setPollRevision] = useState(0);
  const refreshHistory = () => request<Summary[]>("/runs").then(setHistory);
  useEffect(() => {
    request<Capabilities>("/capabilities")
      .then((c) => {
        setExamples(c.examples);
        setQuestion(c.examples[0]);
        setLive(c.live_configured);
        setPublicDemo(c.public_demo);
      })
      .catch((e) => setError(e.message));
    refreshHistory().catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    setRun(null);
    setComparison(null);
    setReport("");
    if (!selected) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    const update = () =>
      request<Run>("/runs/" + selected)
        .then((r) => {
          if (active) {
            setRun(r);
            if (
              !["completed", "failed", "canceled", "interrupted"].includes(
                r.state,
              )
            )
              timer = setTimeout(update, 700);
          }
        })
        .catch((e) => {
          if (active) {
            setError(e.message);
            timer = setTimeout(update, 2000);
          }
        });
    update();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [selected, pollRevision]);
  useEffect(() => {
    if (!run) return;
    refreshHistory().catch(() => {});
    if (run.state === "completed") {
      let active = true;
      fetchArtifact(`${BASE}/runs/${run.id}/artifacts/comparison.json`)
        .then((r) => r.json())
        .then((c) => {
          if (active) setComparison(c);
        })
        .catch((e) => {
          if (active) setError("Could not load evidence: " + String(e));
        });
      fetchArtifact(`${BASE}/runs/${run.id}/artifacts/report.md`)
        .then((r) => r.text())
        .then((s) => {
          if (active) setReport(s);
        })
        .catch((e) => {
          if (active) setError("Could not load report: " + String(e));
        });
      return () => {
        active = false;
      };
    }
  }, [run?.state, run?.id]);
  const start = async () => {
    setBusy(true);
    setError("");
    try {
      const r = await request<Run>("/runs", "POST", {
        question,
        mode,
        workflow,
        limits: { max_work: budget },
      });
      setSelected(r.id);
      setTab("Findings");
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  };
  const action = async (name: string) => {
    setError("");
    try {
      await request("/runs/" + run!.id + "/" + name, "POST", {});
      setRun(await request<Run>("/runs/" + run!.id));
      setPollRevision((v) => v + 1);
    } catch (e) {
      setError(String(e));
    }
  };
  const active =
    run &&
    !["completed", "failed", "canceled", "interrupted"].includes(run.state);
  const total = run?.plan
    ? (run.plan.treatments.length + 1) * run.plan.seeds.length
    : 0;
  const artifact = (name: string) =>
    `${BASE}/runs/${run?.id}/artifacts/${name}`;
  return (
    <div className="shell">
      <aside className="rail">
        <a className="brand" href="/">
          R
          <span>
            REDLINE<small>RESEARCH COPILOT</small>
          </span>
        </a>
        <div className="rail-label">WORKSPACE</div>
        <button
          className="nav active"
          onClick={() => document.getElementById("question")?.focus()}
        >
          <span>◈</span> Research lab
        </button>
        <a
          className="nav"
          href={
            publicDemo
              ? "https://github.com/asoracca/redline-exchange"
              : "http://127.0.0.1:8000/"
          }
          target="_blank"
          rel="noreferrer"
        >
          <span>⇄</span>{" "}
          {publicDemo ? "Source & local app ↗" : "Exchange demo ↗"}
        </a>
        <div className="rail-label history-label">
          RUN HISTORY <span>{history.length}</span>
        </div>
        <div className="history">
          {history.length === 0 ? (
            <p className="quiet">Your experiments will appear here.</p>
          ) : (
            history.map((h) => (
              <button
                key={h.id}
                className={
                  "history-item " + (h.id === selected ? "selected" : "")
                }
                onClick={() => setSelected(h.id)}
              >
                <span className={"dot " + h.state} />
                <span>
                  {h.question}
                  <small>
                    {h.state} ·{" "}
                    {new Date(h.created * 1000).toLocaleDateString()}
                  </small>
                </span>
              </button>
            ))
          )}
        </div>
        <div className="local">
          <span className="dot completed" />{" "}
          {publicDemo ? "PUBLIC DEMO" : "LOCAL WORKSPACE"}
          <small>
            {publicDemo
              ? "Shared temporary example history"
              : "SQLite checkpoints · single worker"}
          </small>
        </div>
      </aside>
      <main>
        <header>
          <span>
            WORKSPACE <b>/</b> RESEARCH LAB
          </span>
          <span className="badge">◉ SYNTHETIC SIMULATION</span>
        </header>
        <section className="intro">
          <div className="eyebrow">ASK. EXPERIMENT. VERIFY.</div>
          <h1>
            From a question
            <br />
            to <em>checked evidence.</em>
          </h1>
          <p>
            A bounded research workflow for market microstructure.
            <br />
            Real simulations. Traceable results. No real-market claims.
          </p>
        </section>
        {publicDemo && (
          <div className="finding-note public-notice">
            Public demo · example questions only · real simulations with
            scripted planning. All runs are shared. Only the latest 50 runs are
            retained, and history may reset when the free host restarts. Live AI
            is disabled. Do not enter private information.
          </div>
        )}
        <section className="composer">
          <div className="section-title">
            <h2>What would you like to investigate?</h2>
            <span className="small-tag">
              {mode === "offline" ? "SCRIPTED PLANNING" : "LIVE AI PLANNING"}
            </span>
          </div>
          <label className="sr-only" htmlFor="question">
            Research question
          </label>
          <textarea
            id="question"
            readOnly={publicDemo}
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={1500}
          />
          <div className="examples">
            {examples.slice(0, 6).map((q, i) => (
              <button key={q} onClick={() => setQuestion(q)}>
                {
                  [
                    "Quote latency",
                    "Inventory limits",
                    "Risk & return",
                    "Volatility",
                    "Spread width",
                    "Python vs C++",
                  ][i]
                }{" "}
                ↗
              </button>
            ))}
          </div>
          <div className="composer-footer">
            <div>
              <label>
                Planning{" "}
                <select
                  aria-label="Planning mode"
                  disabled={publicDemo}
                  value={mode}
                  onChange={(e) => setMode(e.target.value)}
                >
                  <option value="offline">Offline · scripted</option>
                  <option value="live" disabled={publicDemo}>
                    Live AI {live ? "" : "· needs configuration"}
                  </option>
                </select>
              </label>
              <label>
                Workflow{" "}
                <select
                  aria-label="Workflow"
                  value={workflow}
                  onChange={(e) => setWorkflow(e.target.value)}
                >
                  <option value="staged">Staged review</option>
                  <option value="single_agent">Single-agent baseline</option>
                </select>
              </label>
            </div>
            <button
              className="primary"
              onClick={start}
              disabled={busy || question.length < 5}
            >
              {busy ? "Starting…" : "Run experiment"} <span>↗</span>
            </button>
          </div>
          <details className="budget">
            <summary>Resource limits & mode details</summary>
            <label>
              Maximum work units{" "}
              <input
                aria-label="Maximum work units"
                type="number"
                min={40}
                max={100000}
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
              />
            </label>
            <p>
              {publicDemo
                ? "Public runs: 30 seconds, 40 tool calls and 9,000 work units maximum. Six requests per minute across all visitors. Offline planning is scripted; simulations and reports run for real. Live AI is disabled."
                : "120 seconds active time · 100 tool calls · 4 model calls · 6,000 reserved output tokens. Offline plans are prewritten; simulations and reports run for real. Live AI uses your configured model and may incur provider charges. Cost unavailable. No orders reach a broker."}
            </p>
          </details>
        </section>
        {error && (
          <div role="alert" className="error">
            {error}
          </div>
        )}
        {run ? (
          <section className="results">
            <div className="section-title">
              <div>
                <div className="eyebrow">EXPERIMENT {run.id.slice(0, 8)}</div>
                <h2>
                  {run.state === "completed"
                    ? "Evidence, ready to inspect"
                    : run.state === "failed"
                      ? "Run needs attention"
                      : run.state === "canceled"
                        ? "Run canceled"
                        : run.state === "interrupted"
                          ? "Run interrupted"
                          : "Building the evidence"}
                </h2>
              </div>
              <span className={"status " + run.state}>{run.state}</span>
            </div>
            <div className="run-meta">
              <span>
                {run.request.mode === "offline"
                  ? "Offline · scripted planning"
                  : "Live AI"}{" "}
                / {run.request.workflow}
              </span>
              <span>
                {run.completed_tasks}/{total || "—"} tasks · {fmt(run.elapsed)}s
                active
              </span>
              {active && !publicDemo ? (
                <button onClick={() => action("cancel")}>Cancel run</button>
              ) : run.can_resume && !publicDemo ? (
                <button onClick={() => action("resume")}>
                  Resume checkpoints
                </button>
              ) : null}
            </div>
            <ol className="stage-list" aria-label="Research workflow">
              {[
                "Question",
                "Plan",
                "Validate",
                "Simulate",
                "Evidence",
                "Review",
              ].map((stage, index) => {
                const done = [
                  true,
                  !!run.plan,
                  !!run.plan,
                  !!total && run.completed_tasks === total,
                  (run.artifacts ?? []).includes("comparison.json"),
                  !!run.review,
                ][index];
                return (
                  <li key={stage} className={done ? "done" : "pending"}>
                    {done ? "✓ " : "○ "}
                    {stage}
                  </li>
                );
              })}
            </ol>
            <div
              className="progress"
              role="progressbar"
              aria-label="Simulation tasks"
              aria-valuemin={0}
              aria-valuemax={total || 1}
              aria-valuenow={run.completed_tasks}
            >
              <i
                style={{
                  width: total
                    ? `${(100 * run.completed_tasks) / total}%`
                    : "0%",
                }}
              />
            </div>
            {run.error && (
              <div role="alert" className="error">
                {run.error}
                <p>{run.next_action}</p>
              </div>
            )}
            <nav className="tabs">
              {["Findings", "Plan", "Activity & usage", "Artifacts"].map(
                (t) => (
                  <button
                    key={t}
                    className={tab === t ? "chosen" : ""}
                    onClick={() => setTab(t)}
                  >
                    {t}
                  </button>
                ),
              )}
            </nav>
            {tab === "Plan" && (
              <div className="panel">
                {run.plan ? (
                  <>
                    <h3>{run.plan.hypothesis}</h3>
                    <div className="metrics">
                      <div>
                        <small>STEPS / TASK</small>
                        <strong>{run.plan.steps}</strong>
                      </div>
                      <div>
                        <small>SEEDS / GROUP</small>
                        <strong>{run.plan.seeds.length}</strong>
                      </div>
                      <div>
                        <small>SCHEDULED WORK</small>
                        <strong>{fmt(run.plan.estimated_work)}</strong>
                      </div>
                    </div>
                    <h4>Changes from baseline</h4>
                    <div className="table-scroll">
                      <table aria-label="Experiment controls">
                        <thead>
                          <tr>
                            <th>Configuration</th>
                            <th>Control</th>
                            <th>Baseline</th>
                            <th>Treatment</th>
                          </tr>
                        </thead>
                        <tbody>
                          {run.plan.treatments.flatMap((t) =>
                            Object.entries(t.parameters)
                              .filter(
                                ([key, value]) =>
                                  value !==
                                  run.plan!.baseline?.[
                                    key as keyof typeof t.parameters
                                  ],
                              )
                              .map(([key, value]) => (
                                <tr key={t.name + key}>
                                  <td>{t.name}</td>
                                  <td>{key.replaceAll("_", " ")}</td>
                                  <td>
                                    {String(
                                      run.plan!.baseline?.[
                                        key as keyof typeof t.parameters
                                      ],
                                    )}
                                  </td>
                                  <td>{String(value)}</td>
                                </tr>
                              )),
                          )}
                        </tbody>
                      </table>
                    </div>
                    <p className="method">
                      Seeds: {run.plan.seeds.join(", ")}. Simulation treatments
                      use separate seed offsets; comparisons use exploratory,
                      unadjusted intervals.
                    </p>
                    <ul>
                      {run.plan.assumptions.map((a) => (
                        <li key={a}>{a}</li>
                      ))}
                    </ul>
                    <details>
                      <summary>Validated plan JSON</summary>
                      <pre>{JSON.stringify(run.plan, null, 2)}</pre>
                    </details>
                  </>
                ) : (
                  <p>{run.explanation || "Waiting for a validated plan."}</p>
                )}
              </div>
            )}
            {tab === "Findings" && (
              <div className="panel">
                {comparison ? (
                  <>
                    <div className="finding-note">
                      ↳{" "}
                      {run.review?.assessment === "inconclusive"
                        ? "Some differences remain uncertain. Inspect intervals before drawing conclusions."
                        : "Directional differences observed within this synthetic experiment."}{" "}
                      No strong configuration ranking is asserted.
                    </div>
                    <img
                      className="chart"
                      src={artifact("chart.svg")}
                      alt="Scenario means and exploratory 95 percent intervals"
                    />
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Configuration / metric</th>
                            <th>n</th>
                            <th>Mean</th>
                            <th>Sample SD</th>
                            <th>95% interval</th>
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(comparison.groups).flatMap(
                            ([name, metrics]) =>
                              Object.entries(metrics).map(([metric, s]) => (
                                <tr key={name + metric}>
                                  <td>
                                    <strong>{name}</strong>
                                    <small>{metric.replaceAll("_", " ")}</small>
                                  </td>
                                  <td>{s.n}</td>
                                  <td>{fmt(s.mean)}</td>
                                  <td>{fmt(s.sd)}</td>
                                  <td>
                                    [{fmt(s.low)}, {fmt(s.high)}]
                                  </td>
                                </tr>
                              )),
                          )}
                        </tbody>
                      </table>
                    </div>
                    <p className="method">
                      {comparison.method} {comparison.seed_schedule}
                    </p>
                    <h3>
                      Research report{" "}
                      <a
                        href={artifact("report.md")}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open artifact ↗
                      </a>
                    </h3>
                    <div className="report">
                      {report.split("\n").map((line, i) => (
                        <p key={i}>
                          {line
                            .split(/(\[[^\]]+\]\([a-z-]+\.(?:json|csv|svg)\))/g)
                            .map((part, j) => {
                              const match = part.match(
                                /^\[([^\]]+)\]\(([a-z-]+\.(?:json|csv|svg))\)$/,
                              );
                              return match ? (
                                <a
                                  key={j}
                                  href={artifact(match[2])}
                                  target="_blank"
                                  rel="noreferrer"
                                >
                                  {match[1]} ↗
                                </a>
                              ) : (
                                <React.Fragment key={j}>
                                  {part
                                    .replace(/^#+ /, "")
                                    .replaceAll("**", "")}
                                </React.Fragment>
                              );
                            })}
                        </p>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="empty">
                    <span>◈</span>
                    <h3>
                      {active
                        ? "The worker is running your experiment."
                        : "No completed report for this run."}
                    </h3>
                    <p>
                      {active
                        ? "Follow validated actions in Activity & usage."
                        : "Inspect the explanation, plan and action log. No missing experiments are silently excluded."}
                    </p>
                  </div>
                )}
              </div>
            )}
            {tab === "Activity & usage" && (
              <div className="panel">
                <div className="budget-status" aria-label="Budget usage">
                  Work {fmt(run.work)} /{" "}
                  {fmt(run.request.limits?.max_work ?? 40000)} · Tools{" "}
                  {run.tools} / {run.request.limits?.max_tools ?? 100} · Model
                  calls {run.model_calls} /{" "}
                  {run.request.limits?.max_model_calls ?? 4}
                </div>
                <div className="metrics">
                  <div>
                    <small>TOOLS / MODEL CALLS</small>
                    <strong>
                      {run.tools} / {run.model_calls}
                    </strong>
                  </div>
                  <div>
                    <small>INPUT / OUTPUT TOKENS</small>
                    <strong>
                      {run.input_tokens ?? "—"} / {run.output_tokens ?? "—"}
                    </strong>
                  </div>
                  <div>
                    <small>COST</small>
                    <strong>Unavailable</strong>
                  </div>
                </div>
                <p className="method">
                  {run.request.mode === "offline"
                    ? "No model was called. Planning and review are scripted."
                    : run.usage_complete
                      ? "Provider-reported usage is available for every response."
                      : "Usage is incomplete: some attempts returned no token counts. Totals shown are only the reported portion."}{" "}
                  These are action summaries, not hidden reasoning.
                </p>
                {(run.events ?? []).map((e) => (
                  <details className="event" key={e.seq}>
                    <summary>
                      <span
                        className={
                          "dot " + (e.ok === false ? "failed" : "completed")
                        }
                      />
                      <b>{e.kind}</b> {e.summary}
                      <small>
                        {e.duration_ms != null ? `${e.duration_ms} ms` : ""}
                      </small>
                    </summary>
                    <pre>{JSON.stringify(e, null, 2)}</pre>
                  </details>
                ))}
              </div>
            )}
            {tab === "Artifacts" && (
              <div className="panel artifact-grid">
                {(run.artifacts ?? []).map((n) => (
                  <a
                    key={n}
                    href={artifact(n)}
                    target="_blank"
                    rel="noreferrer"
                  >
                    <span>↗</span>
                    {n}
                  </a>
                ))}
                {(run.artifacts ?? []).length === 0 && (
                  <p>Artifacts appear as validated stages finish.</p>
                )}
              </div>
            )}
          </section>
        ) : (
          <section className="welcome">
            <div>
              <span>01</span>
              <h3>Plan within the model</h3>
              <p>
                Supported controls, explicit assumptions and a finite work
                budget.
              </p>
            </div>
            <div>
              <span>02</span>
              <h3>Run across seeds</h3>
              <p>
                Python schedules experiments and calculates every reported
                number.
              </p>
            </div>
            <div>
              <span>03</span>
              <h3>Inspect the evidence</h3>
              <p>
                Checked claims, uncertainty intervals and durable source
                provenance.
              </p>
            </div>
          </section>
        )}
        <footer>
          REDLINE RESEARCH COPILOT{" "}
          <span>Artificial markets. Real engineering.</span>
        </footer>
      </main>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
