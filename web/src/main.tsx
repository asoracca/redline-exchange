import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import type { components } from "./contracts";
import "./style.css";
type Snapshot = components["schemas"]["Snapshot"];
type Event = components["schemas"]["Event"];
type SymbolName = "AAPL" | "MSFT" | "NVDA" | "DEMO";
type Command = Event["command"];
type Draft = Command extends infer C
  ? C extends Command
    ? Omit<C, "request_id" | "symbol">
    : never
  : never;
const symbols: SymbolName[] = ["AAPL", "MSFT", "NVDA", "DEMO"];
const money = (n: number) => `$${(n / 100).toFixed(2)}`;
const steps: { label: string; symbol: SymbolName; command: Draft }[] = [
  {
    label: "Clear DEMO for the lesson. The saved journal is retained.",
    symbol: "DEMO",
    command: { kind: "RESET" },
  },
  {
    label: "An expensive seller arrives first: 100 shares at $101.05.",
    symbol: "DEMO",
    command: {
      kind: "LIMIT",
      order_id: "seller-high",
      side: "SELL",
      quantity: 100,
      price_ticks: 10105,
    },
  },
  {
    label: "A cheaper seller arrives next: 100 shares at $101.00.",
    symbol: "DEMO",
    command: {
      kind: "LIMIT",
      order_id: "seller-low",
      side: "SELL",
      quantity: 100,
      price_ticks: 10100,
    },
  },
  {
    label:
      "Buy 130: the cheapest seller fills 100 at $101.00, then 30 at $101.05.",
    symbol: "DEMO",
    command: {
      kind: "MARKET",
      order_id: "buyer-130",
      side: "BUY",
      quantity: 130,
    },
  },
  {
    label: "Queue a second seller at $101.05, behind the remaining 70 shares.",
    symbol: "DEMO",
    command: {
      kind: "LIMIT",
      order_id: "seller-later",
      side: "SELL",
      quantity: 50,
      price_ticks: 10105,
    },
  },
  {
    label:
      "Buy 80: FIFO fills the older 70 shares, then 10 from the later seller.",
    symbol: "DEMO",
    command: {
      kind: "MARKET",
      order_id: "buyer-fifo",
      side: "BUY",
      quantity: 80,
    },
  },
  {
    label: "Clear MSFT to demonstrate an independent book.",
    symbol: "MSFT",
    command: { kind: "RESET" },
  },
  {
    label: "A $200.00 MSFT bid cannot match the $101.05 DEMO ask.",
    symbol: "MSFT",
    command: {
      kind: "LIMIT",
      order_id: "isolated-bid",
      side: "BUY",
      quantity: 25,
      price_ticks: 20000,
    },
  },
];
async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`Request failed (${r.status})`);
  return r.json();
}
function App() {
  const [live, setLive] = useState<Snapshot>();
  const [historical, setHistorical] = useState<Snapshot>();
  const [symbol, setSymbol] = useState<SymbolName>("DEMO");
  const [message, setMessage] = useState(
    "Start the guided scenario or enter your own synthetic order.",
  );
  const [connected, setConnected] = useState(false);
  const [busy, setBusy] = useState(false);
  const [step, setStep] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [replayCursor, setReplayCursor] = useState<number>();
  const [replayEnd, setReplayEnd] = useState(0);
  const [orderId, setOrderId] = useState("my-order");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [qty, setQty] = useState("130");
  const [price, setPrice] = useState("101.05");
  const [kind, setKind] = useState<"LIMIT" | "MARKET">("LIMIT");
  const [latency, setLatency] = useState<number>();
  const pending = useRef<Command | undefined>(undefined);
  const gate = useRef(false);
  useEffect(() => {
    let disposed = false;
    let source: EventSource | undefined;
    let timer: ReturnType<typeof setTimeout>;
    async function connect() {
      try {
        const snap = await get<Snapshot>("/api/snapshot");
        if (disposed) return;
        acceptSnapshot(snap);
        source = new EventSource(`/api/events?cursor=${snap.seq}`);
        source.addEventListener("snapshot", (e) => {
          acceptSnapshot(JSON.parse((e as MessageEvent).data));
          setConnected(true);
        });
        source.onerror = () => {
          setConnected(false);
          source?.close();
          timer = setTimeout(connect, 1000);
        };
      } catch {
        if (!disposed) timer = setTimeout(connect, 1000);
      }
    }
    void connect();
    return () => {
      disposed = true;
      clearTimeout(timer);
      source?.close();
    };
  }, []);
  function acceptSnapshot(next: Snapshot) {
    setLive((previous) =>
      !previous ||
      previous.session_id !== next.session_id ||
      next.seq >= previous.seq
        ? next
        : previous,
    );
  }
  const snapshot = historical ?? live;
  const book = snapshot?.books[symbol];
  async function send(
    draft: Draft,
    target: SymbolName = symbol,
    retry = false,
  ) {
    if (gate.current) return false;
    gate.current = true;
    setBusy(true);
    const c =
      retry && pending.current
        ? pending.current
        : ({
            ...draft,
            symbol: target,
            request_id: crypto.randomUUID(),
          } as Command);
    pending.current = c;
    const start = performance.now();
    try {
      const r = await fetch("/api/commands", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(c),
      });
      if (!r.ok) {
        pending.current = undefined;
        throw new Error(`Command failed (${r.status})`);
      }
      const event: Event = await r.json();
      pending.current = undefined;
      acceptSnapshot(await get<Snapshot>("/api/snapshot"));
      setLatency(performance.now() - start);
      setMessage(
        event.accepted
          ? `${c.kind} accepted · event ${event.seq} · ${event.trades.length} fills`
          : `Rejected: ${event.error}`,
      );
      if (!event.accepted) setPlaying(false);
      return event.accepted;
    } catch (e) {
      setMessage(
        `${String(e)}${pending.current ? " · Retry uses the same request ID." : ""}`,
      );
      setPlaying(false);
      return false;
    } finally {
      setBusy(false);
      gate.current = false;
    }
  }
  async function advance() {
    if (replayCursor !== undefined) {
      const next = Math.min(replayCursor + 1, replayEnd);
      try {
        const r = await get<components["schemas"]["ReplayResult"]>(
          `/api/replay?through=${next}`,
        );
        setHistorical(r.snapshot);
        setReplayCursor(next);
        setMessage(`Saved session replay · event ${next}/${replayEnd}`);
        if (next === replayEnd) setPlaying(false);
      } catch (e) {
        setMessage(String(e));
        setPlaying(false);
      }
      return;
    }
    if (step >= steps.length) {
      setPlaying(false);
      return;
    }
    const s = steps[step];
    setSymbol(s.symbol);
    if (await send(s.command, s.symbol)) {
      setMessage(s.label);
      setStep(step + 1);
      if (step + 1 === steps.length) setPlaying(false);
    }
  }
  useEffect(() => {
    if (!playing || busy) return;
    const timer = setTimeout(() => void advance(), 1000);
    return () => clearTimeout(timer);
  }, [playing, busy, step, replayCursor]);
  async function replay() {
    setPlaying(false);
    try {
      const result =
        await get<components["schemas"]["ReplayResult"]>("/api/replay");
      setReplayEnd(result.snapshot.seq);
      setReplayCursor(0);
      setHistorical(
        (
          await get<components["schemas"]["ReplayResult"]>(
            "/api/replay?through=0",
          )
        ).snapshot,
      );
      setMessage(
        "Verified: saved events reproduce identical final state and trades. Step through the saved session.",
      );
    } catch (e) {
      setMessage(String(e));
    }
  }
  function submit(e: React.FormEvent) {
    e.preventDefault();
    const quantity = Number(qty);
    const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(price);
    if (kind === "LIMIT" && !match) {
      setMessage("Use a dollar price with at most two decimal places.");
      return;
    }
    const price_ticks = match
      ? Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"))
      : 0;
    void send(
      kind === "LIMIT"
        ? { kind, order_id: orderId, side, quantity, price_ticks }
        : { kind, order_id: orderId, side, quantity },
    );
  }
  return (
    <main>
      <header>
        <div className="brand">
          <span className="mark">R</span>
          <div>
            <strong>REDLINE</strong>
            <small>EXCHANGE LABORATORY</small>
          </div>
        </div>
        <span className="mode">Synthetic simulation</span>
        <span className="connection">
          {connected ? "Local service connected" : "Reconnecting…"}
        </span>
      </header>
      <div className="intro">
        <div>
          <span className="eyebrow">PRICE · TIME · PRIORITY</span>
          <h1>Inside the order book.</h1>
          <p>Place an order. Watch it match. Replay every decision.</p>
        </div>
        <div className="disclosure">
          All prices and orders are synthetic.
          <br />
          Ticker labels are examples. No exchange or brokerage connection.
        </div>
      </div>
      <nav aria-label="Symbols">
        {symbols.map((s) => (
          <button
            key={s}
            className={s === symbol ? "selected" : ""}
            onClick={() => setSymbol(s)}
          >
            {s}
            <small>SIM</small>
          </button>
        ))}
        <span>Tick $0.01 · quantity in whole shares</span>
      </nav>
      <section className="lesson">
        <div>
          <span className="eyebrow">
            {historical
              ? "SAVED SESSION REPLAY"
              : `GUIDED SCENARIO · ${step}/${steps.length}`}
          </span>
          <h2>
            {historical
              ? `Event ${replayCursor} of ${replayEnd}`
              : "Cheapest first. Earliest next."}
          </h2>
          <p role="status">{message}</p>
        </div>
        <div className="controls">
          <button
            onClick={() => setPlaying(!playing)}
            disabled={busy || (!historical && step === steps.length)}
          >
            {playing ? "Pause" : "Play"}
          </button>
          <button
            onClick={() => void advance()}
            disabled={
              busy ||
              playing ||
              (historical ? replayCursor === replayEnd : step === steps.length)
            }
          >
            Single step
          </button>
          <button onClick={() => void replay()} disabled={busy}>
            Replay saved session
          </button>
          {historical && (
            <button
              onClick={() => {
                setHistorical(undefined);
                setReplayCursor(undefined);
                setPlaying(false);
              }}
            >
              Return to current book
            </button>
          )}
        </div>
      </section>
      <div className="grid">
        <section className="panel depth">
          <div className="section-title">
            <h2>{symbol} depth</h2>
            <span>
              {historical ? "REPLAY" : "SIMULATED"} · event {snapshot?.seq ?? 0}
            </span>
          </div>
          <div className="book-halves">
            {(["bids", "asks"] as const).map((key) => (
              <div key={key}>
                <h3 className={key}>
                  {key === "bids" ? "Bids / buyers" : "Asks / sellers"}
                </h3>
                <div className="level heading">
                  <span>Price</span>
                  <span>Shares</span>
                  <span>Orders</span>
                </div>
                {book?.[key].map((l) => (
                  <div
                    className={`level ${key}`}
                    key={l.price_ticks}
                    style={{
                      background: `linear-gradient(to left, ${key === "bids" ? "#123d34" : "#49252a"} ${Math.min(100, l.quantity / 2)}%, transparent 0)`,
                    }}
                  >
                    <strong>{money(l.price_ticks)}</strong>
                    <span>{l.quantity}</span>
                    <span>{l.order_count}</span>
                  </div>
                ))}
                {!book?.[key].length && (
                  <p className="empty">No resting {key}</p>
                )}
              </div>
            ))}
          </div>
          <p className="footnote">
            Best price at the top. Trades execute at the resting seller or
            buyer’s price.
          </p>
        </section>
        <section className="panel entry">
          <h2>Enter an order</h2>
          <form onSubmit={submit}>
            <fieldset disabled={busy || !!historical || playing}>
              <label>
                Order ID
                <input
                  required
                  pattern="[A-Za-z0-9_-]{1,64}"
                  value={orderId}
                  onChange={(e) => setOrderId(e.target.value)}
                />
              </label>
              <div className="pair">
                <label>
                  Side
                  <select
                    aria-label="Side"
                    value={side}
                    onChange={(e) => setSide(e.target.value as "BUY" | "SELL")}
                  >
                    <option>BUY</option>
                    <option>SELL</option>
                  </select>
                </label>
                <label>
                  Type
                  <select
                    aria-label="Type"
                    value={kind}
                    onChange={(e) =>
                      setKind(e.target.value as "LIMIT" | "MARKET")
                    }
                  >
                    <option>LIMIT</option>
                    <option>MARKET</option>
                  </select>
                </label>
              </div>
              <div className="pair">
                <label>
                  Shares
                  <input
                    type="number"
                    min="1"
                    max="1000000"
                    step="1"
                    required
                    value={qty}
                    onChange={(e) => setQty(e.target.value)}
                  />
                </label>
                <label>
                  Limit price ($)
                  <input
                    disabled={kind === "MARKET"}
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                  />
                </label>
              </div>
              <button className="primary" type="submit">
                Submit {side.toLowerCase()} · {symbol}
              </button>
            </fieldset>
          </form>
          {pending.current && (
            <button
              disabled={busy}
              onClick={() => void send({ kind: "RESET" }, symbol, true)}
            >
              Retry last command
            </button>
          )}
          <p className="footnote">
            Simulation only. Market remainders are canceled.
          </p>
        </section>
        <section className="panel">
          <div className="section-title">
            <h2>Recent trades</h2>
            <span>{book?.trades.length ?? 0} fills</span>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Fill</th>
                  <th>Price</th>
                  <th>Shares</th>
                  <th>Maker → taker</th>
                </tr>
              </thead>
              <tbody>
                {book?.trades
                  .slice(-20)
                  .reverse()
                  .map((t) => (
                    <tr key={t.sequence}>
                      <td>#{t.sequence}</td>
                      <td>{money(t.price_ticks)}</td>
                      <td>{t.quantity}</td>
                      <td>
                        {t.maker_order_id} → {t.taker_order_id}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {!book?.trades.length && (
              <p className="empty">
                No trades yet. Step through the scenario to see a fill.
              </p>
            )}
          </div>
        </section>
        <section className="panel">
          <div className="section-title">
            <h2>Resting orders</h2>
            <button
              disabled={busy || !!historical || playing}
              onClick={() => {
                void send({ kind: "RESET" });
                setStep(0);
              }}
            >
              Reset {symbol}
            </button>
          </div>
          <p className="footnote">
            Replace uses the shares and price fields above. Same-price
            reductions retain priority.
          </p>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>ID / side</th>
                  <th>Remaining</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {book?.orders.map((o) => (
                  <tr key={o.order_id}>
                    <td>
                      {o.order_id}
                      <small>
                        {o.side} · {money(o.price_ticks ?? 0)}
                      </small>
                    </td>
                    <td>{o.remaining}</td>
                    <td>
                      <button
                        aria-label={`Replace ${o.order_id}`}
                        disabled={busy || !!historical || playing}
                        onClick={() => {
                          const m = /^(\d+)(?:\.(\d{1,2}))?$/.exec(price);
                          if (!m) {
                            setMessage("Use a valid cent price.");
                            return;
                          }
                          void send({
                            kind: "REPLACE",
                            order_id: o.order_id,
                            quantity: Number(qty),
                            price_ticks:
                              Number(m[1]) * 100 +
                              Number((m[2] ?? "").padEnd(2, "0")),
                          });
                        }}
                      >
                        Replace
                      </button>{" "}
                      <button
                        aria-label={`Cancel ${o.order_id}`}
                        disabled={busy || !!historical || playing}
                        onClick={() =>
                          void send({ kind: "CANCEL", order_id: o.order_id })
                        }
                      >
                        Cancel
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!book?.orders.length && <p className="empty">No active orders</p>}
          </div>
        </section>
      </div>
      <footer>
        <span>
          {snapshot?.backend === "cpp"
            ? "C++17 core · Python adapter"
            : "Python reference engine"}{" "}
          · SQLite journal · epoch {book?.epoch ?? 0}
        </span>
        <span>
          {latency
            ? `Last command + refresh: ${latency.toFixed(1)} ms`
            : "Latency appears after a command"}{" "}
          · local demo, not exchange capacity
        </span>
      </footer>
    </main>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
