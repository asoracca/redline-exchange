import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from pathlib import Path


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def sanitize(value):
    if isinstance(value, str):
        key = os.getenv("OPENAI_API_KEY")
        if key:
            value = value.replace(key, "[REDACTED]")
        return re.sub(
            r"(?:sk-[A-Za-z0-9_-]{8,}|Bearer\s+[A-Za-z0-9._~+/-]+=*)",
            "[REDACTED]",
            value,
        )
    if isinstance(value, dict):
        return {
            k: (
                "[REDACTED]"
                if any(
                    w in k.lower()
                    for w in ["api_key", "authorization", "password", "secret"]
                )
                else sanitize(v)
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [sanitize(x) for x in value]
    return value


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        import fcntl

        self.lease = (self.root / "research.lock").open("a")
        try:
            fcntl.flock(self.lease, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.lease.close()
            raise RuntimeError("Research store already open in another process")
        self.lock = threading.RLock()
        self.db = sqlite3.connect(
            self.root / "research.sqlite3",
            check_same_thread=False,
            isolation_level=None,
        )
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        version = self.db.execute("PRAGMA user_version").fetchone()[0]
        if version == 0:
            self.db.executescript("""BEGIN IMMEDIATE;
            CREATE TABLE runs(id TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE events(seq INTEGER PRIMARY KEY, run_id TEXT NOT NULL, data TEXT NOT NULL);
            CREATE INDEX events_run ON events(run_id,seq);
            CREATE TABLE tasks(run_id TEXT NOT NULL, key TEXT NOT NULL, data TEXT NOT NULL, PRIMARY KEY(run_id,key));
            CREATE TABLE cache(key TEXT PRIMARY KEY, data TEXT NOT NULL);
            CREATE TABLE artifacts(run_id TEXT NOT NULL, name TEXT NOT NULL, content TEXT NOT NULL, PRIMARY KEY(run_id,name));
            PRAGMA user_version=1; COMMIT;""")
        elif version != 1:
            self.close()
            raise RuntimeError("Unsupported research store schema")

    def close(self):
        self.db.close()
        self.lease.close()

    def create(self, request, source):
        with self.lock:
            if self.db.execute("SELECT COUNT(*) FROM runs").fetchone()[0] >= 100:
                raise ValueError(
                    "Local history limit of 100 runs reached; choose another research directory"
                )
            run = dict(
                id=uuid.uuid4().hex,
                request=sanitize(request),
                source=source,
                state="draft",
                plan=None,
                explanation="",
                created=time.time(),
                elapsed=0.0,
                tools=0,
                model_calls=0,
                output_reserved=0,
                input_tokens=None,
                output_tokens=None,
                cost_usd=None,
                usage_complete=True,
                work=0,
                cancel_requested=False,
                completed_tasks=0,
                revision=0,
                review=None,
                error=None,
                failure_code=None,
            )
            self.db.execute(
                "INSERT INTO runs VALUES (?,?)", (run["id"], canonical(run))
            )
            return run

    def get(self, rid):
        with self.lock:
            row = self.db.execute("SELECT data FROM runs WHERE id=?", (rid,)).fetchone()
            if not row:
                raise KeyError("Unknown run")
            return json.loads(row[0])

    def update(self, rid, **changes):
        with self.lock:
            run = self.get(rid)
            run.update(sanitize(changes))
            self.db.execute("UPDATE runs SET data=? WHERE id=?", (canonical(run), rid))
            return run

    def transition(self, rid, state):
        """A state change and its ordered event commit together."""
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.update(rid, state=state)
                self.event(rid, "state", state)
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def prepare_resume(self, rid, **changes):
        """Retain tasks, but never expose a previous attempt's certification."""
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.update(rid, **changes)
                self.db.execute(
                    "DELETE FROM artifacts WHERE run_id=? AND name IN ('report.md','review.json','evidence.json','logs.json')",
                    (rid,),
                )
                self.update(rid, review=None)
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def list(self):
        with self.lock:
            return [
                json.loads(r[0])
                for r in self.db.execute("SELECT data FROM runs ORDER BY rowid DESC")
            ]

    def event(self, rid, kind, summary, **details):
        with self.lock:
            value = sanitize(
                dict(time=time.time(), kind=kind, summary=summary, **details)
            )
            self.db.execute(
                "INSERT INTO events(run_id,data) VALUES (?,?)", (rid, canonical(value))
            )

    def events(self, rid):
        with self.lock:
            return [
                dict(seq=r[0], **json.loads(r[1]))
                for r in self.db.execute(
                    "SELECT seq,data FROM events WHERE run_id=? ORDER BY seq", (rid,)
                )
            ]

    def task(self, rid, key):
        with self.lock:
            row = self.db.execute(
                "SELECT data FROM tasks WHERE run_id=? AND key=?", (rid, key)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def tasks(self, rid):
        with self.lock:
            return [
                json.loads(r[0])
                for r in self.db.execute(
                    "SELECT data FROM tasks WHERE run_id=? ORDER BY key", (rid,)
                )
            ]

    def cache_get(self, key):
        with self.lock:
            row = self.db.execute(
                "SELECT data FROM cache WHERE key=?", (key,)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def save_task(self, rid, key, result, cache_key=None):
        with self.lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self.db.execute(
                    "INSERT OR REPLACE INTO tasks VALUES (?,?,?)",
                    (rid, key, canonical(result)),
                )
                if cache_key:
                    self.db.execute(
                        "INSERT OR IGNORE INTO cache VALUES (?,?)",
                        (cache_key, canonical(result)),
                    )
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise

    def prune_public(self, keep=49, protected=()):
        """Evict only explicitly public terminal runs; local research is never pruned."""
        with self.lock:
            rows = self.list()
            if any(r.get("audience") != "public_demo" for r in rows):
                raise ValueError("Public demo requires a separate public-only store")
            candidates = [
                r
                for r in reversed(rows)
                if r["id"] not in protected
                and r["state"] in {"completed", "failed", "canceled", "interrupted"}
            ]
            remove = candidates[: max(0, len(rows) - keep)]
            self.db.execute("BEGIN IMMEDIATE")
            try:
                for run in remove:
                    rid = run["id"]
                    for table in ("events", "tasks", "artifacts"):
                        self.db.execute(f"DELETE FROM {table} WHERE run_id=?", (rid,))
                    self.db.execute("DELETE FROM runs WHERE id=?", (rid,))
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
            return [r["id"] for r in remove]

    def artifact(self, rid, name, content):
        if name not in ARTIFACTS:
            raise ValueError("Artifact destination not authorized")
        with self.lock:
            self.db.execute(
                "INSERT OR REPLACE INTO artifacts VALUES (?,?,?)",
                (rid, name, sanitize(content)),
            )

    def artifact_get(self, rid, name):
        if name not in ARTIFACTS:
            raise KeyError("Unknown artifact")
        with self.lock:
            row = self.db.execute(
                "SELECT content FROM artifacts WHERE run_id=? AND name=?", (rid, name)
            ).fetchone()
            if not row:
                raise KeyError("Artifact not generated")
            return row[0]

    def artifact_names(self, rid):
        with self.lock:
            return [
                r[0]
                for r in self.db.execute(
                    "SELECT name FROM artifacts WHERE run_id=? ORDER BY name", (rid,)
                )
            ]


ARTIFACTS = {
    "plan.json",
    "results.json",
    "results.csv",
    "comparison.json",
    "chart.svg",
    "chart-inputs.json",
    "report.md",
    "evidence.json",
    "logs.json",
    "review.json",
}
