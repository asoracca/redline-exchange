import json
from pathlib import Path
from research_copilot.evaluate import evaluate


def test_versioned_evaluation(tmp_path):
    dataset = Path(__file__).resolve().parents[2] / "evaluations/research-v1.json"
    cases = json.loads(dataset.read_text())["cases"]
    assert len([c for c in cases if c["category"] == "supported"]) >= 5
    result = evaluate(dataset, tmp_path)
    assert len(result["rows"]) == 32
    assert all(r["passed"] for r in result["rows"])
    assert all(r["status"] == "not run" for r in result["live_evaluation"])
