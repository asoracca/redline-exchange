import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from .boundary import LocalBoundary
from .schemas import Command, Event, ReplayResult, Snapshot
from .service import Capacity, Conflict, Exchange


def create_app(path=None, backend=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.exchange = Exchange(
            path or os.getenv("REDLINE_DB", "redline.sqlite3"),
            backend or os.getenv("REDLINE_BACKEND", "python"),
        )
        app.state.streams = 0
        yield
        app.state.exchange.close()

    app = FastAPI(title="Redline synthetic exchange", lifespan=lifespan)

    app.add_middleware(LocalBoundary)

    @app.get("/api/snapshot", response_model=Snapshot)
    def snapshot():
        return app.state.exchange.snapshot()

    @app.post("/api/commands", response_model=Event)
    def command(command: Command):
        try:
            return app.state.exchange.submit(command)
        except Conflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except Capacity as exc:
            raise HTTPException(429, str(exc)) from exc

    @app.get("/api/replay", response_model=ReplayResult)
    def replay(through: int | None = Query(None, ge=0)):
        try:
            return ReplayResult(
                verified=True, snapshot=app.state.exchange.replay(through)
            )
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/events")
    async def events(request: Request, cursor: int = Query(0, ge=0)):
        try:
            cursor = int(request.headers.get("last-event-id", cursor))
            initial, snap = app.state.exchange.catchup(cursor)
        except ValueError as exc:
            raise HTTPException(409, "Invalid cursor; fetch /api/snapshot") from exc
        if app.state.streams >= 8:
            raise HTTPException(429, "Eight stream limit")
        app.state.streams += 1

        def frame(kind, value, seq=None):
            prefix = "" if seq is None else f"id: {seq}\n"
            return f"{prefix}event: {kind}\ndata: {value.model_dump_json()}\n\n"

        async def stream():
            nonlocal cursor
            try:
                # A coherent initial cut: committed events, then snapshot at that cursor.
                for event in initial:
                    yield frame("exchange", event, event.seq)
                yield frame("snapshot", snap, snap.seq)
                cursor = snap.seq
                while not await request.is_disconnected():
                    await asyncio.sleep(0.25)
                    pending, state = app.state.exchange.catchup(cursor)
                    for event in pending:
                        yield frame("exchange", event, event.seq)
                    if pending:
                        yield frame("snapshot", state, state.seq)
                        cursor = state.seq
                    else:
                        yield ": heartbeat\n\n"
            finally:
                app.state.streams -= 1

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    dist = Path(__file__).resolve().parents[2] / "web/dist"
    if dist.exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="demo")
    return app
