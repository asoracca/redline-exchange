"""Research API with explicit local and restricted public-demo modes."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from exchange.boundary import LocalBoundary
from .models import StartRequest
from .contracts import Capabilities, RunSummary, RunView
from .planner import describe
from .workflow import Manager
from .tools import SCHEMAS
from .public_demo import PublicDemo


def create_app(root=None):
    public = os.getenv("REDLINE_PUBLIC_DEMO") == "1"
    policy = PublicDemo() if public else None
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME") or os.getenv("REDLINE_PUBLIC_HOST")
    if public and (not host or any(c in host for c in "/*: ")):
        raise ValueError("Public demo needs one explicit public hostname")

    @asynccontextmanager
    async def lifespan(app):
        app.state.manager = Manager(
            root
            or os.getenv(
                "REDLINE_RESEARCH_DIR",
                ".research-public" if public else ".research-data",
            )
        )
        try:
            if public and any(
                r.get("audience") != "public_demo"
                for r in app.state.manager.store.list()
            ):
                raise ValueError("Refusing to publish a local/private research store")
            yield
        finally:
            app.state.manager.close()

    app = FastAPI(
        title="Redline Research Copilot — local synthetic research", lifespan=lifespan
    )
    app.add_middleware(LocalBoundary)
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"]
        + ([host] if public else []),
    )

    @app.exception_handler(KeyError)
    async def missing(request, exc):
        from fastapi.responses import JSONResponse

        return JSONResponse({"detail": "Unknown run or artifact"}, status_code=404)

    @app.get("/healthz")
    def health():
        return {"status": "ok", "mode": "public_demo" if public else "local"}

    @app.get("/api/research/capabilities", response_model=Capabilities)
    def capabilities():
        return dict(
            **describe(),
            public_demo=public,
            live_configured=not public
            and bool(os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL")),
            live_verification="not run",
            tool_schemas={k: v.model_json_schema() for k, v in SCHEMAS.items()},
        )

    @app.get("/api/research/runs", response_model=list[RunSummary])
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

    @app.post("/api/research/runs", status_code=202, response_model=RunView)
    def start(request: StartRequest):
        try:
            if policy:
                request = policy.prepare(request)
            return view(app.state.manager.start(request, public=public))
        except ValueError as exc:
            raise HTTPException(429, str(exc)) from exc

    def view(run):
        exhausted = run.get("failure_code") in {
            "budget",
            "question_rejected",
            "question_mismatch",
        }
        changed = run["source"] != app.state.manager.source
        resumable = (
            not public
            and not exhausted
            and not changed
            and run["state"] in {"failed", "canceled", "interrupted"}
            and run.get("resume_count", 0) < 3
        )
        guidance = (
            "Revise the question or increase the budget, then start a new experiment."
            if exhausted
            else "Source or runtime changed; start a new experiment."
            if changed
            else "Resume skips completed tasks and keeps the original budgets."
            if resumable
            else "Start a new experiment; checkpoint resume is unavailable."
        )
        return dict(**run, can_resume=resumable, next_action=guidance)

    @app.get("/api/research/runs/{rid}", response_model=RunView)
    def get(rid: str):
        store = app.state.manager.store
        return dict(
            **view(store.get(rid)),
            events=store.events(rid),
            artifacts=store.artifact_names(rid),
        )

    @app.post("/api/research/runs/{rid}/cancel", response_model=RunView)
    def cancel(rid: str):
        if public:
            raise HTTPException(
                403, "Shared public runs cannot be canceled by visitors"
            )
        return view(app.state.manager.cancel(rid))

    @app.post(
        "/api/research/runs/{rid}/resume", status_code=202, response_model=RunView
    )
    def resume(rid: str):
        if public:
            raise HTTPException(
                403, "Use a new example run; resume is available in the local app"
            )
        try:
            return view(app.state.manager.resume(rid))
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

        @app.get("/", include_in_schema=False)
        def home():
            return FileResponse(dist / "research.html")

        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")
    return app
