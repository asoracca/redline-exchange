"""Opt-in, credentialed comparison; never invoked by CI or offline evaluation."""

import argparse
import json
import os
import time
from pathlib import Path
from .models import StartRequest
from .storage import canonical
from .workflow import Manager


def evaluate_live(dataset, output):
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("OPENAI_MODEL"):
        raise SystemExit(
            "Live evaluation not run: configure OPENAI_API_KEY and OPENAI_MODEL"
        )
    root = Path(output)
    rows = []
    for workflow in ("staged", "single_agent"):
        manager = Manager(root / workflow)
        try:
            for case in json.loads(Path(dataset).read_text())["cases"]:
                if "fixture" in case:
                    rows.append(
                        dict(
                            id=case["id"],
                            workflow=workflow,
                            status="not run",
                            reason="Statistical fixture exercised by deterministic evaluation, not a live prompt",
                        )
                    )
                    continue
                started = time.perf_counter()
                run = manager.start(
                    StartRequest(
                        question=case["question"], mode="live", workflow=workflow
                    ),
                    background=False,
                )
                valid = (
                    run["state"] == "completed"
                    if case["expect"] == "completed"
                    else run.get("decision_outcome") == case["expect"]
                    and run["work"] == 0
                )
                events = manager.store.events(run["id"])
                rows.append(
                    dict(
                        id=case["id"],
                        category=case["category"],
                        workflow=workflow,
                        status="run",
                        passed=valid,
                        run_id=run["id"],
                        state=run["state"],
                        error=run["error"],
                        latency_seconds=time.perf_counter() - started,
                        invalid_tool_calls=sum(
                            e["kind"] == "tool" and e.get("ok") is False for e in events
                        ),
                        unsupported_claims=sum(
                            e.get("error_type") == "ValueError"
                            and ("claim" in e["summary"] or "evidence" in e["summary"])
                            for e in events
                        ),
                        input_tokens=run["input_tokens"],
                        output_tokens=run["output_tokens"],
                        cost_usd=None,
                    )
                )
        finally:
            manager.close()
    result = dict(
        dataset_version=1,
        model=os.getenv("OPENAI_MODEL"),
        rows=rows,
        note="One sequential pass; separate stores with identical permissions/budgets. Unsupported claims count rejected evidence-reference checks; numerical report claims are code-rendered. Human assessment of plan/question relevance is still required. No causal multi-agent superiority claim.",
    )
    (root / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="evaluations/research-v1.json")
    parser.add_argument("--output", default="live-evaluation")
    args = parser.parse_args()
    result = evaluate_live(args.dataset, args.output)
    print(canonical(result))
