import time
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from research_copilot.api import create_app
from research_copilot.models import StartRequest
from research_copilot.planner import EXAMPLES
from research_copilot.public_demo import PublicDemo
from research_copilot.workflow import Manager


def test_public_policy_closed_and_bounded():
    policy = PublicDemo()
    for request in (
        StartRequest(question="my private strategy notes"),
        StartRequest(question=EXAMPLES[0], mode="live"),
    ):
        with pytest.raises(HTTPException):
            policy.prepare(request)
    request = StartRequest(question=EXAMPLES[0])
    for _ in range(6):
        constrained = policy.prepare(request)
        assert constrained.mode == "offline" and constrained.limits.max_seconds == 30
        assert constrained.limits.max_work == 9000
    with pytest.raises(HTTPException) as exc:
        policy.prepare(request)
    assert exc.value.status_code == 429


def test_public_api_rejects_private_data_and_provider_calls(tmp_path, monkeypatch):
    monkeypatch.setenv("REDLINE_PUBLIC_DEMO", "1")
    monkeypatch.setenv("REDLINE_PUBLIC_HOST", "demo.example.test")
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setenv("OPENAI_MODEL", "must-not-be-used")
    with TestClient(
        create_app(tmp_path), base_url="https://demo.example.test"
    ) as client:
        assert client.get("/healthz").json()["mode"] == "public_demo"
        caps = client.get("/api/research/capabilities").json()
        assert caps["public_demo"] and not caps["live_configured"]
        assert (
            client.post(
                "/api/research/runs", json={"question": "private arbitrary question"}
            ).status_code
            == 400
        )
        assert (
            client.post(
                "/api/research/runs", json={"question": EXAMPLES[0], "mode": "live"}
            ).status_code
            == 403
        )
        assert client.get("/api/research/runs").json() == []
        response = client.post("/api/research/runs", json={"question": EXAMPLES[0]})
        assert response.status_code == 202
        rid = response.json()["id"]
        for _ in range(200):
            run = client.get("/api/research/runs/" + rid).json()
            if run["state"] in ("completed", "failed"):
                break
            time.sleep(0.01)
        assert run["state"] == "completed", run["error"]
        assert run["model_calls"] == 0 and run["audience"] == "public_demo"
        assert client.post("/api/research/runs/" + rid + "/cancel").status_code == 403
        assert client.post("/api/research/runs/" + rid + "/resume").status_code == 403
        assert (
            client.post(
                "/api/research/runs",
                json={"question": EXAMPLES[0]},
                headers={"Origin": "https://evil.test"},
            ).status_code
            == 403
        )
        assert client.get("/healthz", headers={"Host": "evil.test"}).status_code == 400
        assert (
            client.get(f"/api/research/runs/{rid}/artifacts/report.md").status_code
            == 200
        )


def test_public_refuses_existing_local_store(tmp_path, monkeypatch):
    manager = Manager(tmp_path)
    manager.start(StartRequest(question=EXAMPLES[0]), background=False)
    manager.close()
    monkeypatch.setenv("REDLINE_PUBLIC_DEMO", "1")
    monkeypatch.setenv("REDLINE_PUBLIC_HOST", "demo.example.test")
    with pytest.raises(ValueError, match="private research store"):
        with TestClient(create_app(tmp_path)):
            pass


def test_public_pruning_never_removes_active_or_local_runs(tmp_path):
    manager = Manager(tmp_path)
    try:
        r = manager.start(
            StartRequest(question=EXAMPLES[0]), background=False, public=True
        )
        active = manager.store.create(
            StartRequest(question=EXAMPLES[1]).model_dump(), manager.source
        )
        manager.store.update(active["id"], audience="public_demo")
        assert manager.store.prune_public(keep=1) == [r["id"]]
        assert manager.store.events(r["id"]) == []
        assert manager.store.tasks(r["id"]) == []
        assert manager.store.artifact_names(r["id"]) == []
        assert manager.store.get(active["id"])["state"] == "draft"
        manager.store.update(active["id"], audience="local")
        with pytest.raises(ValueError):
            manager.store.prune_public(keep=0)
        assert manager.store.get(active["id"])
    finally:
        manager.close()


def test_public_requires_specific_hostname(tmp_path, monkeypatch):
    monkeypatch.setenv("REDLINE_PUBLIC_DEMO", "1")
    monkeypatch.setenv("REDLINE_PUBLIC_HOST", "*")
    with pytest.raises(ValueError, match="hostname"):
        create_app(tmp_path)
