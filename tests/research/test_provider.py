import json
import httpx
import pytest
from research_copilot.models import PlanningDecision, StartRequest
from research_copilot.planner import EXAMPLES, offline_plan
from research_copilot.provider import OpenAIProvider, ProviderError, strict_schema
from research_copilot.workflow import Context, Manager
from research_copilot.storage import canonical


@pytest.fixture
def live(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-credential-never-log")
    monkeypatch.setenv("OPENAI_MODEL", "configured-test-model")
    m = Manager(tmp_path)
    r = m.store.create(
        StartRequest(question=EXAMPLES[0], mode="live").model_dump(), m.source
    )
    yield m, Context(m.store, r["id"])
    m.close()


def body(decision):
    return dict(
        status="completed",
        usage={"input_tokens": 70, "output_tokens": 20},
        output=[
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": decision.model_dump_json()}
                ],
            }
        ],
    )


def test_adapter_structured_output_retry_usage_and_secrets(live):
    m, ctx = live
    calls = []

    def handler(req):
        value = json.loads(req.content)
        calls.append(value)
        assert req.url == "https://api.openai.com/v1/responses"
        assert value["model"] == "configured-test-model" and value["store"] is False
        assert value["text"]["format"]["strict"] is True
        assert "tools" not in value
        if len(calls) == 1:
            return httpx.Response(429)
        return httpx.Response(200, json=body(offline_plan(EXAMPLES[0])))

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = OpenAIProvider(client).request(
            "planner", {"question": EXAMPLES[0]}, PlanningDecision, ctx
        )
    assert result.outcome == "planned" and len(calls) == 2
    r = m.store.get(ctx.rid)
    assert (
        r["input_tokens"] == 70 and r["output_tokens"] == 20 and r["cost_usd"] is None
    )
    assert "test-credential-never-log" not in canonical(m.store.events(ctx.rid))
    m.store.event(ctx.rid, "untrusted", "test-credential-never-log")
    assert "test-credential-never-log" not in canonical(m.store.events(ctx.rid))


@pytest.mark.parametrize(
    "reply",
    [
        {"status": "incomplete"},
        {"status": "completed", "output": []},
        {
            "status": "completed",
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": '{"shell":"execute this command"}',
                        }
                    ],
                }
            ],
        },
    ],
)
def test_invalid_responses_never_semantically_retried(live, reply):
    m, ctx = live
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=reply))
    ) as client:
        with pytest.raises(ProviderError):
            OpenAIProvider(client).request("planner", {}, PlanningDecision, ctx)
    assert m.store.get(ctx.rid)["model_calls"] == 1
    assert m.store.get(ctx.rid)["input_tokens"] is None


def test_schema_is_closed_recursively():
    schema = strict_schema(PlanningDecision.model_json_schema())

    def check(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for v in node.values():
                check(v)
        if isinstance(node, list):
            for v in node:
                check(v)

    check(schema)


def test_missing_configuration_is_readable(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    m = Manager(tmp_path)
    try:
        r = m.start(StartRequest(question=EXAMPLES[0], mode="live"), background=False)
        assert r["state"] == "failed" and "OPENAI_API_KEY" in r["error"]
        assert r["input_tokens"] is None and r["model_calls"] == 0
    finally:
        m.close()


def test_live_workflow_rejects_reviewer_fake_citation(live):
    from research_copilot.models import ReviewDecision

    m, _ = live

    class FakeProvider:
        def request(self, role, data, schema, budget):
            if schema is PlanningDecision:
                return offline_plan(EXAMPLES[0])
            return ReviewDecision(
                assessment="relevant", concerns=[], evidence_ids=["nonexistent.result"]
            )

    m.provider = FakeProvider()
    run = m.start(StartRequest(question=EXAMPLES[0], mode="live"), background=False)
    assert run["state"] == "failed" and "nonexistent evidence" in run["error"]
    assert "report.md" not in m.store.artifact_names(run["id"])
