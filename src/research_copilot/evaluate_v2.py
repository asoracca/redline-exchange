"""Same-case scripted/live evaluation with frozen splits and explicit denominators."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
import time
from typing import Literal

from pydantic import Field, model_validator
from . import experiments
from .models import Limits, ReportArgs, StartRequest, StrictModel
from .provider import OpenAIProvider
from .spending import SpendingBudget
from .storage import canonical
from .workflow import Manager


class Case(StrictModel):
    id: str
    split: Literal["development", "held_out"]
    category: Literal["supported", "ambiguous", "unsupported", "injection"]
    question: str
    expect: Literal["completed", "clarify", "unsupported"]
    controls: dict[str, int | float]
    baseline: dict[str, int | float]
    metrics: list[str]


class Dataset(StrictModel):
    version: Literal[2]
    protocol: Literal["scripted-vs-live-v2"]
    notes: str
    cases: list[Case] = Field(min_length=2)

    @model_validator(mode="after")
    def distinct(self):
        if len({c.id for c in self.cases}) != len(self.cases):
            raise ValueError("Case IDs must be unique")
        if len({c.question.strip().lower() for c in self.cases}) != len(self.cases):
            raise ValueError("Questions must not leak across splits")
        if {c.split for c in self.cases} != {"development", "held_out"}:
            raise ValueError("Both evaluation splits required")
        for case in self.cases:
            if (case.category == "supported") != (case.expect == "completed"):
                raise ValueError("Supported cases must expect completion")
        return self


# Identical caps for scripted and live; never raised to rescue one failed case.
EVALUATION_LIMITS = Limits(
    max_work=12000,
    max_tools=40,
    max_model_calls=4,
    max_output_tokens=6000,
    max_seconds=60,
)


def rate(values):
    """Wilson 95% interval, descriptive across this authored set of cases."""
    n, k = len(values), sum(values)
    if not n:
        return dict(numerator=0, denominator=0, rate=None, wilson95=None)
    p, z = k / n, 1.96
    center = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return dict(
        numerator=k,
        denominator=n,
        rate=p,
        wilson95=[max(0, center - half), min(1, center + half)],
    )


def plan_matches(case, plan):
    if not plan or plan["kind"] != "simulation":
        return False
    # A preregistered, narrow automated oracle; not a semantic LLM judge.
    treatments = [t["parameters"] for t in plan["treatments"]]
    return (
        all(plan["baseline"].get(k) == v for k, v in case.baseline.items())
        and all(
            any(
                t.get(k) == v and t.get(k) != plan["baseline"].get(k)
                for t in treatments
            )
            for k, v in case.controls.items()
        )
        and set(case.metrics) <= set(plan["metrics"])
    )


def verify_evidence(manager, run):
    """Recalculate from seed records; verify exact report and artifact digests."""
    from .models import ExperimentPlan

    rid = run["id"]

    def get(name):
        return manager.store.artifact_get(rid, name)

    try:
        plan = ExperimentPlan.model_validate(run["plan"])
        rows = json.loads(get("results.json"))
        for row in rows:
            i, j = map(int, row["key"].split(":"))
            experiments.validate_result(plan, i, j, row)
        computed = experiments.compare(plan, rows)
        if computed != json.loads(get("comparison.json")):
            return False
        claims = ReportArgs(
            claims=[
                dict(evidence_id=e["id"], conclusion=e["conclusion"])
                for e in computed["evidence"].values()
            ]
        )
        report = experiments.render_report(plan, computed, claims.claims, run["review"])
        if report != get("report.md"):
            return False
        manifest = json.loads(get("evidence.json"))
        required = {
            "plan.json",
            "results.json",
            "results.csv",
            "comparison.json",
            "report.md",
            "review.json",
            "chart.svg",
            "chart-inputs.json",
            "logs.json",
        }
        return required <= set(manifest["artifact_sha256"]) and all(
            hashlib.sha256(get(name).encode()).hexdigest() == sha
            for name, sha in manifest["artifact_sha256"].items()
        )
    except (KeyError, ValueError, TypeError, IndexError):
        return False


def score(case, manager, mode):
    started = time.perf_counter()
    run = manager.start(
        StartRequest(
            question=case.question,
            mode=mode,
            workflow="staged",
            limits=EVALUATION_LIMITS,
        ),
        background=False,
    )
    latency = time.perf_counter() - started
    completed = run["state"] == "completed"
    evidence = verify_evidence(manager, run) if completed else None
    relevant = plan_matches(case, run["plan"]) if case.expect == "completed" else None
    rejected = (
        run.get("decision_outcome") == case.expect
        and run["work"] == 0
        and run["plan"] is None
    )
    passed = (
        completed and relevant and evidence if case.expect == "completed" else rejected
    )
    return dict(
        id=case.id,
        split=case.split,
        category=case.category,
        expected=case.expect,
        mode=mode,
        status="measured",
        run_id=run["id"],
        state=run["state"],
        outcome=run.get("decision_outcome"),
        passed=bool(passed),
        valid_plan=run["plan"] is not None,
        plan_matches_oracle=relevant,
        evidence_correct=evidence,
        appropriate_rejection=rejected if case.expect != "completed" else None,
        latency_seconds=latency,
        model_calls=run["model_calls"],
        input_tokens=0 if mode == "offline" else run["input_tokens"],
        output_tokens=0 if mode == "offline" else run["output_tokens"],
        usage_complete=run.get("usage_complete", False),
        limits=EVALUATION_LIMITS.model_dump(),
        work=run["work"],
        error=run["error"],
        failure_code=run.get("failure_code"),
        failure_example=None
        if passed
        else dict(
            question=case.question,
            expected=case.expect,
            actual=run.get("decision_outcome") or run["state"],
            explanation=run["explanation"],
            error=run["error"],
        ),
        plan=run["plan"],
        review=run["review"],
    )


def summarize(rows):
    measured = [r for r in rows if r["status"] == "measured"]
    supported = [r for r in measured if r["expected"] == "completed"]
    rejection = [r for r in measured if r["expected"] != "completed"]
    completed = [r for r in measured if r["state"] == "completed"]
    times = sorted(r["latency_seconds"] for r in measured)
    return dict(
        measured_cases=len(measured),
        unmeasured_cases=len(rows) - len(measured),
        expected_outcome=rate([r["passed"] for r in measured]),
        task_completion=rate([r["state"] == "completed" for r in supported]),
        valid_plan=rate([r["valid_plan"] for r in supported]),
        plan_relevance_oracle=rate([r["plan_matches_oracle"] for r in supported]),
        evidence_correctness=rate([r["evidence_correct"] for r in completed]),
        appropriate_rejection=rate([r["appropriate_rejection"] for r in rejection]),
        latency_seconds=dict(
            n=len(times),
            median=statistics.median(times) if times else None,
            p95=times[max(0, math.ceil(0.95 * len(times)) - 1)] if times else None,
        ),
        usage=dict(
            complete_cases=sum(r["usage_complete"] for r in measured),
            measured_cases=len(measured),
            reported_input_tokens=sum(r["input_tokens"] or 0 for r in measured)
            if any(r["input_tokens"] is not None for r in measured)
            else None,
            reported_output_tokens=sum(r["output_tokens"] or 0 for r in measured)
            if any(r["output_tokens"] is not None for r in measured)
            else None,
        ),
        failure_examples=[r["failure_example"] for r in measured if not r["passed"]],
    )


def evaluate(dataset, output, split="development", spending=None):
    path, destination = Path(dataset), Path(output)
    data = Dataset.model_validate_json(path.read_text())
    cases = [c for c in data.cases if split == "all" or c.split == split]
    if not cases:
        raise ValueError("No cases for requested split")
    if (destination / "results.json").exists():
        raise ValueError("Results already exist; use a fresh output directory")
    destination.mkdir(parents=True, exist_ok=True)
    rows = []
    source = experiments.provenance()
    modes = ("offline", "live") if spending else ("offline",)
    for mode in modes:
        for case in cases:
            # Every case and mode starts cold; no cache/order advantage.
            with tempfile.TemporaryDirectory() as directory:
                manager = Manager(directory, provider=OpenAIProvider(spending=spending))
                try:
                    row = score(case, manager, mode)
                    rows.append(row)
                    folder = destination / "runs" / mode / case.id
                    folder.mkdir(parents=True, exist_ok=True)
                    for name in manager.store.artifact_names(row["run_id"]):
                        (folder / name).write_text(
                            manager.store.artifact_get(row["run_id"], name)
                        )
                    (folder / "run.json").write_text(
                        canonical(manager.store.get(row["run_id"])) + "\n"
                    )
                    (folder / "events.json").write_text(
                        canonical(manager.store.events(row["run_id"])) + "\n"
                    )
                finally:
                    manager.close()
            # Preserve completed rows if the evaluator itself is interrupted.
            (destination / "partial-rows.json").write_text(
                json.dumps(rows, indent=2) + "\n"
            )
    if not spending:
        rows.extend(
            dict(
                id=c.id,
                split=c.split,
                category=c.category,
                mode="live",
                status="unmeasured",
                reason="Credentials and spending budget not authorized for this run",
            )
            for c in cases
        )
    summaries = {
        f"{mode}/{part}": summarize(
            [r for r in rows if r["mode"] == mode and r["split"] == part]
        )
        for mode in ("offline", "live")
        for part in sorted({c.split for c in cases})
    }
    result = dict(
        dataset_version=2,
        dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        protocol=data.protocol,
        created_utc=datetime.now(timezone.utc).isoformat(),
        source=source,
        limits=EVALUATION_LIMITS.model_dump(),
        model=os.getenv("OPENAI_MODEL") if spending else None,
        comparison="scripted baseline versus live staged workflow; no multi-agent advantage tested",
        split_notes=data.notes,
        rows=rows,
        summary=summaries,
    )
    (destination / "results.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# Research evaluation v2",
        "",
        "Scripted and live use identical cases, limits and tools; each case starts cold. Live rows marked unmeasured are not failures and have no estimated model-quality score.",
        "",
        "| Mode / split | Expected outcome | Completion | Valid plan | Plan relevance oracle | Evidence | Appropriate rejection |",
        "|---|---|---|---|---|---|---|",
    ]
    metrics = (
        "expected_outcome",
        "task_completion",
        "valid_plan",
        "plan_relevance_oracle",
        "evidence_correctness",
        "appropriate_rejection",
    )
    for label, s in summaries.items():
        cells = [
            f"{s[m]['numerator']}/{s[m]['denominator']}"
            if s[m]["denominator"]
            else "unmeasured / no eligible cases"
            for m in metrics
        ]
        lines.append("| " + " | ".join([label] + cells) + " |")
    lines += [
        "",
        "Raw JSON includes Wilson 95% intervals, all denominators, median/p95 latency, usage coverage and failure examples. These intervals describe a small authored suite, not a random sample of all user questions. Evidence correctness is conditional on completed runs; it measures deterministic arithmetic/references, not model truthfulness. The plan oracle checks declared controls/metrics, not full scientific relevance. Latency includes orchestration, simulation, provider waits (if live) and SQLite, excluding HTTP/browser. No live quality or multi-agent superiority follows from mock tests.",
        "",
        data.notes,
        "",
        "Held-out paraphrases are intentionally absent from the scripted template lookup. Do not broaden that lookup to erase measured failures; use a new dataset version for further tuning.",
        "",
        "## Failure examples",
    ]
    for label, s in summaries.items():
        for f in s["failure_examples"]:
            lines.append(
                f"- {label}: {f['question']} Expected {f['expected']}; got {f['actual']}."
            )
    (destination / "RESULTS.md").write_text("\n".join(lines) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default="evaluations/research-v2.json")
    parser.add_argument("--output", default="evaluation-v2")
    parser.add_argument(
        "--split", choices=["development", "held_out", "all"], default="development"
    )
    parser.add_argument(
        "--authorize-live",
        action="store_true",
        help="Explicitly authorize credentialed provider calls",
    )
    parser.add_argument("--budget-usd", type=float)
    parser.add_argument("--input-usd-per-million", type=float)
    parser.add_argument("--output-usd-per-million", type=float)
    args = parser.parse_args()
    spending = None
    if args.authorize_live:
        if not os.getenv("OPENAI_API_KEY") or not os.getenv("OPENAI_MODEL"):
            parser.error("Live run requires explicit OPENAI_API_KEY and OPENAI_MODEL")
        try:
            spending = SpendingBudget(
                args.budget_usd,
                args.input_usd_per_million,
                args.output_usd_per_million,
                Path(args.output) / "budget.json",
            )
        except ValueError as exc:
            parser.error(str(exc))
    elif any(
        v is not None
        for v in (
            args.budget_usd,
            args.input_usd_per_million,
            args.output_usd_per_million,
        )
    ):
        parser.error("Budget arguments require --authorize-live")
    result = evaluate(args.dataset, args.output, args.split, spending)
    print(canonical(result["summary"]))


if __name__ == "__main__":
    main()
