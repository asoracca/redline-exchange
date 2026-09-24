"""Adversarial software tests use mocked transports, never live model evidence."""

import json
import sqlite3
import threading

import httpx
import pytest
from pydantic import ValidationError

from research_copilot.models import PlanningDecision, ReviewDecision, StartRequest
from research_copilot.planner import EXAMPLES, offline_plan
from research_copilot.provider import OpenAIProvider, ProviderError
from research_copilot.spending import SpendingBudget, SpendingLimit
from research_copilot.workflow import Context, Manager, StopRun
from research_copilot.evaluate_v2 import Dataset, evaluate, rate, verify_evidence


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-not-real-key")
    monkeypatch.setenv("OPENAI_MODEL", "test-not-real-model")
    m = Manager(tmp_path)
    r = m.store.create(
        StartRequest(question=EXAMPLES[0], mode="live").model_dump(), m.source
    )
    yield m, Context(m.store, r["id"])
    m.close()


@pytest.mark.parametrize(
    "body",
    [
        [],
        None,
        {"status": "completed", "output": {}},
        {"status": "completed", "output": [None]},
        {"status": "completed", "output": [{"type": "message", "content": None}]},
        {
            "status": "completed",
            "output": [
                {"type": "message", "content": [{"type": "refusal", "refusal": "no"}]}
            ],
        },
        {"status": "completed", "usage": [], "output": []},
    ],
)
def test_malformed_provider_envelopes_are_safe_and_not_retried(setup, body):
    m, ctx = setup
    calls = []

    def respond(req):
        calls.append(req)
        return httpx.Response(200, content=json.dumps(body))

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(ProviderError):
            OpenAIProvider(client).request("planner", {}, PlanningDecision, ctx)
    assert len(calls) == 1
    assert m.store.get(ctx.rid)["model_calls"] == 1


@pytest.mark.parametrize(
    "payload,match", [(b"not json", "invalid JSON"), (b"x" * 256001, "256 KB")]
)
def test_bounded_invalid_response(setup, payload, match):
    _, ctx = setup
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=payload))
    ) as client:
        with pytest.raises(ProviderError, match=match):
            OpenAIProvider(client).request("planner", {}, PlanningDecision, ctx)


def test_timeouts_charge_two_attempts_and_mark_usage_unknown(setup):
    m, ctx = setup

    def timeout(req):
        raise httpx.ReadTimeout("do not log provider data", request=req)

    with httpx.Client(transport=httpx.MockTransport(timeout)) as client:
        with pytest.raises(ProviderError, match="two attempts"):
            OpenAIProvider(client).request("planner", {}, PlanningDecision, ctx)
    run = m.store.get(ctx.rid)
    assert run["model_calls"] == 2 and run["output_reserved"] == 5000
    assert run["input_tokens"] is None and not run["usage_complete"]


def test_cancel_during_retry_prevents_second_request(setup):
    m, ctx = setup
    calls = []

    def respond(req):
        calls.append(req)
        m.cancel(ctx.rid)
        return httpx.Response(429)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with pytest.raises(StopRun):
            OpenAIProvider(client).request("planner", {}, PlanningDecision, ctx)
    assert len(calls) == 1


def test_consistent_planning_decisions():
    with pytest.raises(ValidationError, match="Only a planned"):
        PlanningDecision(outcome="planned", explanation="missing plan", plan=None)
    with pytest.raises(ValidationError):
        PlanningDecision(
            outcome="unsupported",
            explanation="contradiction",
            plan=offline_plan(EXAMPLES[0]).plan,
        )


def test_reviewer_mismatch_is_not_certified(setup):
    m, _ = setup

    class Mismatch:
        def request(self, role, data, schema, budget):
            if schema is PlanningDecision:
                return offline_plan(EXAMPLES[0])
            return ReviewDecision(
                assessment="question_mismatch",
                concerns=["question_mismatch"],
                evidence_ids=[],
            )

    m.provider = Mismatch()
    r = m.start(StartRequest(question=EXAMPLES[0], mode="live"), background=False)
    assert r["state"] == "failed" and r["failure_code"] == "question_mismatch"
    assert "review.json" in m.store.artifact_names(r["id"])
    assert "report.md" not in m.store.artifact_names(r["id"])
    with pytest.raises(ValueError, match="Revise"):
        m.resume(r["id"])


def test_evidence_checker_detects_fabricated_comparison(setup):
    m, _ = setup
    r = m.start(StartRequest(question=EXAMPLES[0]), background=False)
    assert verify_evidence(m, r)
    data = json.loads(m.store.artifact_get(r["id"], "comparison.json"))
    next(iter(data["evidence"].values()))["delta"] = 999999
    m.store.artifact(r["id"], "comparison.json", json.dumps(data))
    assert not verify_evidence(m, r)


def test_checkpoint_transaction_rolls_back_cache_failure(setup):
    m, ctx = setup
    m.store.db.execute(
        "CREATE TRIGGER reject_cache BEFORE INSERT ON cache BEGIN SELECT RAISE(ABORT, 'fixture'); END"
    )
    with pytest.raises(sqlite3.IntegrityError, match="fixture"):
        m.store.save_task(ctx.rid, "0:0", {"value": 1}, "cache-key")
    assert m.store.task(ctx.rid, "0:0") is None
    assert m.store.cache_get("cache-key") is None


def test_spending_stops_before_network_and_keeps_ledger(setup, tmp_path):
    _, ctx = setup
    budget = SpendingBudget(0.000001, 1, 1, tmp_path / "budget.json")
    calls = []

    def forbidden(req):
        calls.append(req)
        raise AssertionError("must never send")

    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        with pytest.raises(SpendingLimit, match="no request sent"):
            OpenAIProvider(client, spending=budget).request(
                "planner", {}, PlanningDecision, ctx
            )
    assert calls == []
    assert json.loads((tmp_path / "budget.json").read_text())["reserved_usd"] == 0
    with pytest.raises(ValueError, match="ledger exists"):
        SpendingBudget(1, 1, 1, tmp_path / "budget.json")


def test_wilson_denominators():
    assert rate([])["rate"] is None
    r = rate([True] * 5)
    assert r["numerator"] == r["denominator"] == 5
    assert 0.5 < r["wilson95"][0] < 1 and r["wilson95"][1] == 1


def test_v2_dataset_and_scripted_evaluation_never_call_provider(tmp_path, monkeypatch):
    from pathlib import Path

    def forbidden(*args, **kwargs):
        raise AssertionError("No live authorization")

    monkeypatch.setattr(OpenAIProvider, "request", forbidden)
    path = Path("evaluations/research-v2.json")
    dataset = Dataset.model_validate_json(path.read_text())
    assert len(dataset.cases) == 24
    result = evaluate(path, tmp_path / "eval", split="development")
    summary = result["summary"]["offline/development"]
    assert summary["expected_outcome"]["numerator"] == 12
    assert summary["task_completion"]["denominator"] == 5
    assert result["summary"]["live/development"]["measured_cases"] == 0
    assert result["model"] is None
    assert all(
        r["limits"] == result["limits"]
        for r in result["rows"]
        if r["status"] == "measured"
    )


def test_held_out_not_in_scripted_lookup():
    from pathlib import Path

    cases = Dataset.model_validate_json(
        Path("evaluations/research-v2.json").read_text()
    ).cases
    for case in cases:
        if case.split == "held_out" and case.category == "supported":
            assert offline_plan(case.question).outcome != "planned"


def test_active_provider_cancellation_is_observed_before_using_response(setup):
    m, ctx = setup
    entered, released = threading.Event(), threading.Event()

    def respond(req):
        entered.set()
        assert released.wait(3)
        return httpx.Response(200, json={"status": "completed", "output": []})

    errors = []

    def request():
        with httpx.Client(transport=httpx.MockTransport(respond)) as client:
            try:
                OpenAIProvider(client).request("planner", {}, PlanningDecision, ctx)
            except StopRun:
                errors.append("canceled")

    worker = threading.Thread(target=request)
    worker.start()
    assert entered.wait(3)
    m.cancel(ctx.rid)
    released.set()
    worker.join(3)
    assert errors == ["canceled"]


def test_state_event_transaction_rolls_back_together(setup):
    m, ctx = setup
    before = m.store.get(ctx.rid)["state"]
    m.store.db.execute(
        "CREATE TRIGGER reject_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'fixture'); END"
    )
    with pytest.raises(sqlite3.IntegrityError, match="fixture"):
        m.state(ctx.rid, "running")
    assert m.store.get(ctx.rid)["state"] == before


def test_resume_invalidates_previous_certification(setup):
    m, _ = setup
    r = m.start(StartRequest(question=EXAMPLES[0]), background=False)
    assert "report.md" in m.store.artifact_names(r["id"])
    m.store.prepare_resume(r["id"], state="draft", error=None)
    assert m.store.get(r["id"])["review"] is None
    assert len(m.store.tasks(r["id"])) == 12
    assert not {"report.md", "evidence.json", "review.json", "logs.json"} & set(
        m.store.artifact_names(r["id"])
    )
