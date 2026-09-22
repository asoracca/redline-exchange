"""One serialized writer, durable journal, deterministic reconstruction."""

import json
import sqlite3
import threading
import uuid
from dataclasses import asdict
from pathlib import Path

from pydantic import TypeAdapter
from orderbook import LimitOrderBook, Side
from orderbook.native import NativeLimitOrderBook
from .schemas import Command, Event, Snapshot

SYMBOLS = ("AAPL", "MSFT", "NVDA", "DEMO")
MAX_EVENTS = 2000


class Conflict(ValueError):
    pass


class Capacity(ValueError):
    pass


class Exchange:
    def __init__(self, path: str, backend="python"):
        if backend not in ("python", "cpp"):
            raise ValueError("backend must be python or cpp")
        self.backend = backend
        self.factory = LimitOrderBook if backend == "python" else NativeLimitOrderBook
        self.lock = threading.RLock()
        self.lease = None
        if path != ":memory:":
            # POSIX local demo: refuse multiple writers, even across processes.
            import fcntl

            self.lease = open(path + ".lock", "a")
            try:
                fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                self.lease.close()
                raise RuntimeError("This journal is already open by another process")
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.execute("PRAGMA synchronous=FULL")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            self.db.executescript(
                (Path(__file__).parent / "migrations/001.sql").read_text()
            )
        elif version != 1:
            self.close()
            raise RuntimeError("Unsupported journal schema")
        self.db.execute("BEGIN IMMEDIATE")
        self.db.execute(
            "INSERT OR IGNORE INTO metadata VALUES (?, ?)",
            ("session_id", str(uuid.uuid4())),
        )
        self.db.execute("COMMIT")
        self.session_id = self.db.execute(
            "SELECT value FROM metadata WHERE key='session_id'"
        ).fetchone()[0]
        self._recover()

    def close(self):
        self.db.close()
        if self.lease:
            self.lease.close()

    def _fresh(self):
        return {s: self.factory(s) for s in SYMBOLS}, dict.fromkeys(SYMBOLS, 0)

    def _apply(self, books, epochs, command):
        c = command
        book = books[c.symbol]
        if c.kind == "RESET":
            books[c.symbol] = self.factory(c.symbol)
            epochs[c.symbol] += 1
            return []
        if c.kind == "LIMIT":
            trades = book.submit_limit(
                c.order_id, Side(c.side), c.quantity, c.price_ticks
            )
        elif c.kind == "MARKET":
            trades = book.submit_market(c.order_id, Side(c.side), c.quantity)
        elif c.kind == "CANCEL":
            book.cancel(c.order_id)
            trades = []
        else:
            trades = book.replace(c.order_id, c.quantity, c.price_ticks)
        return [asdict(t) for t in trades]

    def _run(self, books, epochs, command, seq):
        try:
            trades = self._apply(books, epochs, command)
            return Event(
                seq=seq, command=command, accepted=True, error=None, trades=trades
            )
        except (KeyError, ValueError) as error:
            return Event(
                seq=seq, command=command, accepted=False, error=str(error), trades=[]
            )

    def _reconstruct(self, through=None):
        books, epochs = self._fresh()
        seq = 0
        for raw, result in self.db.execute(
            "SELECT command, result FROM events WHERE seq <= ? ORDER BY seq",
            (MAX_EVENTS if through is None else through,),
        ):
            saved = Event.model_validate_json(result)
            command = TypeAdapter(Command).validate_json(raw)
            actual = self._run(books, epochs, command, saved.seq)
            if actual != saved:
                raise RuntimeError(f"Journal replay mismatch at {saved.seq}")
            seq = saved.seq
        return books, epochs, seq

    def _recover(self):
        self.books, self.epochs, self.seq = self._reconstruct()

    def submit(self, command):
        raw = json.dumps(command.model_dump(), sort_keys=True)
        with self.lock:
            existing = self.db.execute(
                "SELECT command, result FROM events WHERE request_id=?",
                (command.request_id,),
            ).fetchone()
            if existing:
                if existing[0] != raw:
                    raise Conflict("request_id already used for a different command")
                return Event.model_validate_json(existing[1])
            if self.seq >= MAX_EVENTS:
                raise Capacity("Journal limit reached; start with a new database file")
            self.db.execute("BEGIN IMMEDIATE")
            try:
                result = self._run(self.books, self.epochs, command, self.seq + 1)
                self.db.execute(
                    "INSERT INTO events VALUES (?, ?, ?, ?)",
                    (result.seq, command.request_id, raw, result.model_dump_json()),
                )
                self.db.execute("COMMIT")
            except BaseException:
                if self.db.in_transaction:
                    self.db.execute("ROLLBACK")
                self._recover()
                raise
            self.seq = result.seq
            return result

    def _snapshot(self, books, epochs, seq):
        return Snapshot(
            session_id=self.session_id,
            seq=seq,
            backend=self.backend,
            books={
                s: dict(
                    bids=[asdict(x) for x in b.depth(Side.BUY, 20)],
                    asks=[asdict(x) for x in b.depth(Side.SELL, 20)],
                    orders=[asdict(x) for x in b.active_orders()],
                    trades=[asdict(x) for x in b.trade_history()],
                    epoch=epochs[s],
                )
                for s, b in books.items()
            },
        )

    def snapshot(self):
        with self.lock:
            return self._snapshot(self.books, self.epochs, self.seq)

    def replay(self, through=None):
        with self.lock:
            if through is not None and not 0 <= through <= self.seq:
                raise ValueError("cursor is outside this session")
            books, epochs, seq = self._reconstruct(through)
            snapshot = self._snapshot(books, epochs, seq)
            if through is None and snapshot != self.snapshot():
                raise RuntimeError("Final replay state differs")
            return snapshot

    def catchup(self, cursor):
        with self.lock:
            if not 0 <= cursor <= self.seq:
                raise ValueError("cursor is outside this session")
            events = [
                Event.model_validate_json(r[0])
                for r in self.db.execute(
                    "SELECT result FROM events WHERE seq > ? ORDER BY seq", (cursor,)
                )
            ]
            return events, self.snapshot()
