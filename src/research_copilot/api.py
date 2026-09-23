"""Local-only research API and existing exchange demo on the same origin."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from exchange.boundary import LocalBoundary
from .models import StartRequest
from .planner import describe
from .workflow import Manager
from .tools import SCHEMAS


def create_app(root=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.manager = Manager(
            root or os.getenv("REDLINE_RESEARCH_DIR", ".research-data")
        )
        yield
        app.state.manager.close()

    app = FastAPI(
        title="Redline Research Copilot — local synthetic research", lifespan=lifespan
    )
    app.add_middleware(LocalBoundary)
    app.add_middleware(
        TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "testserver"]
    )

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": "Unknown run or artifact"}, status_code=404)

    @app.get("/api/research/capabilities")
    def capabilities():
        return dict(
            **describe(),
            live_configured=bool(
                os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL")
            ),
            live_verification="not run",
            tool_schemas={k: v.model_json_schema() for k, v in SCHEMAS.items()},
        )

    @app.get("/api/research/runs")
    def history():
        return [
            dict(
                id=r["id"],
                question=r["request"]["question"],
                state=r["state"],
                created=r["created"],
                mode=r["request"]["mode"],
            )
            for r in app.state.manager.store.list()
        ]

    @app.post("/api/research/runs", status_code=202)
    def start(request: StartRequest):
        try:
            return app.state.manager.start(request)
        except ValueError as exc:
            raise HTTPException(429, str(exc)) from exc

    @app.get("/api/research/runs/{rid}")
    def get(rid: str):
        store = app.state.manager.store
        return dict(
            **store.get(rid),
            events=store.events(rid),
            artifacts=store.artifact_names(rid),
        )

    @app.post("/api/research/runs/{rid}/cancel")
    def cancel(rid: str):
        return app.state.manager.cancel(rid)

    @app.post("/api/research/runs/{rid}/resume", status_code=202)
    def resume(rid: str):
        try:
            return app.state.manager.resume(rid)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/research/runs/{rid}/artifacts/{name}")
    def artifact(rid: str, name: str):
        content = app.state.manager.store.artifact_get(rid, name)
        mime = (
            "image/svg+xml"
            if name.endswith(".svg")
            else "application/json"
            if name.endswith(".json")
            else "text/plain"
        )
        return Response(
            content,
            media_type=mime,
            headers={
                "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; sandbox",
                "X-Content-Type-Options": "nosniff",
            },
        )

    dist = Path(__file__).resolve().parents[2] / "web/dist"
    if dist.exists():

        @app.get("/")
        def home():
            return FileResponse(dist / "research.html")

        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    return app
