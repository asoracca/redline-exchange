"""Single local worker, durable task checkpoints, bounded model decisions."""

import hashlib
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from .models import ExperimentPlan, PlanningDecision, ReviewDecision
from .planner import offline_plan
from .provider import OpenAIProvider, ProviderError
from .storage import Store, canonical
from .experiments import provenance
from .tools import Registry

TERMINAL = {"completed", "failed", "canceled", "interrupted"}


class StopRun(RuntimeError):
    pass


class BudgetExceeded(RuntimeError):
    pass


class Context:
    def __init__(self, store, rid):
        self.store, self.rid = store, rid
        self.started = time.monotonic()
        self.prior = store.get(rid)["elapsed"]

    def check(self):
        elapsed = self.prior + time.monotonic() - self.started
        run = self.store.update(self.rid, elapsed=elapsed)
        if run["cancel_requested"]:
            raise StopRun(
                "Canceled between bounded tasks; completed checkpoints retained"
            )
        if elapsed >= run["request"]["limits"]["max_seconds"]:
            raise BudgetExceeded(
                "Wall-clock budget exhausted; completed checkpoints retained"
            )
        return run

    def reserve(self, field, amount, limit):
        run = self.check()
        if run[field] + amount > run["request"]["limits"][limit]:
            raise BudgetExceeded(f"{limit} exhausted; no further work started")
        self.store.update(self.rid, **{field: run[field] + amount})

    def reserve_model(self):
        self.reserve("model_calls", 1, "max_model_calls")
        run = self.check()
        tokens = min(
            2500, run["request"]["limits"]["max_output_tokens"] - run["output_reserved"]
        )
        if tokens < 256:
            raise BudgetExceeded("Output token budget exhausted")
        self.reserve("output_reserved", tokens, "max_output_tokens")
        return tokens, min(
            30, max(0.01, run["request"]["limits"]["max_seconds"] - run["elapsed"])
        )

    def log_model(self, model, usage, status):
        run = self.store.get(self.rid)
        safe_usage = {
            k: v
            for k, v in (usage or {}).items()
            if k in ("input_tokens", "output_tokens") and type(v) is int and v >= 0
        }
        for field, value in safe_usage.items():
            self.store.update(self.rid, **{field: (run[field] or 0) + value})
        self.store.event(
            self.rid,
            "model",
            status,
            model=model,
            usage=safe_usage or None,
            cost_usd=None,
        )


class Manager:
    def __init__(self, root, provider=None):
        self.store = Store(root)
        self.provider = provider or OpenAIProvider()
        self.source = provenance()
        self.pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="research")
        self.lock = threading.Lock()
        self.futures = {}
        for run in self.store.list():
            if run["state"] not in TERMINAL:
                self.store.update(
                    run["id"],
                    state="interrupted",
                    error="Process stopped; resume retained checkpoints",
                )
                self.store.event(run["id"], "state", "interrupted")

    def close(self):
        for rid, future in list(self.futures.items()):
            if not future.done():
                self.store.update(rid, cancel_requested=True)
        self.pool.shutdown(wait=True, cancel_futures=False)
        self.store.close()

    def start(self, request, background=True):
        with self.lock:
            if sum(not f.done() for f in self.futures.values()) >= 4:
                raise ValueError("Local queue is full (four runs)")
            run = self.store.create(request.model_dump(), self.source)
            self.store.event(run["id"], "state", "draft")
            if background:
                self.futures[run["id"]] = self.pool.submit(self.work, run["id"])
        if not background:
            self.work(run["id"])
        return self.store.get(run["id"])

    def resume(self, rid):
        with self.lock:
            run = self.store.get(rid)
            if run["state"] not in {"failed", "interrupted", "canceled"}:
                raise ValueError("Only stopped runs may resume")
            if rid in self.futures and not self.futures[rid].done():
                raise ValueError("Run still stopping")
            if run.get("resume_count", 0) >= 3:
                raise ValueError("Three-resume limit reached; start a new run")
            if run["source"] != self.source:
                raise ValueError("Source or runtime changed; start a new run")
            if sum(not f.done() for f in self.futures.values()) >= 4:
                raise ValueError("Local queue full")
            self.store.update(
                rid,
                state="draft",
                cancel_requested=False,
                error=None,
                resume_count=run.get("resume_count", 0) + 1,
            )
            self.futures[rid] = self.pool.submit(self.work, rid)
            return self.store.get(rid)

    def cancel(self, rid):
        run = self.store.get(rid)
        if run["state"] not in TERMINAL:
            self.store.update(rid, cancel_requested=True)
        return self.store.get(rid)

    def state(self, rid, state):
        self.store.update(rid, state=state)
        self.store.event(rid, "state", state)

    def work(self, rid):
        ctx = Context(self.store, rid)
        tools = Registry(ctx)
        try:
            run = ctx.check()
            self.store.update(rid, completed_tasks=len(self.store.tasks(rid)))
            if run["plan"]:
                plan = ExperimentPlan.model_validate(run["plan"])
                self.store.artifact(rid, "plan.json", canonical(plan.model_dump()))
                self.store.event(
                    rid,
                    "checkpoint",
                    "Resuming validated plan; completed tasks are skipped",
                )
            else:
                capabilities = tools.call("describe_simulator", {})
                if run["request"]["mode"] == "offline":
                    decision = offline_plan(run["request"]["question"])
                    self.store.event(
                        rid, "planner", "Scripted offline template; no model called"
                    )
                else:
                    role = (
                        "planner"
                        if run["request"]["workflow"] == "staged"
                        else "single research agent"
                    )
                    decision = self.provider.request(
                        role,
                        dict(
                            question=run["request"]["question"],
                            capabilities=capabilities,
                        ),
                        PlanningDecision,
                        ctx,
                    )
                self.store.update(
                    rid,
                    explanation=decision.explanation,
                    decision_outcome=decision.outcome,
                )
                if decision.outcome != "planned" or decision.plan is None:
                    raise ValueError(decision.explanation)
                plan = tools.call("validate_experiment", decision.plan.model_dump())
            self.state(rid, "validated")
            self.state(rid, "running")
            for i in range(1 + len(plan.treatments)):
                for j in range(len(plan.seeds)):
                    ctx.check()
                    if self.store.task(rid, f"{i}:{j}") is None:
                        tools.call(
                            "run_simulation_batch"
                            if plan.kind == "simulation"
                            else "run_matching_benchmark",
                            dict(scenario=i, seed_index=j),
                        )
            tools.call("load_run_results", {})
            comparison = tools.call("compare_experiments", {})
            self.state(rid, "reviewing")
            concerns = ["synthetic_only"]
            if len(plan.seeds) < 5:
                concerns.append("small_sample")
            if any(
                e["conclusion"] == "inconclusive"
                for e in comparison["evidence"].values()
            ):
                concerns.append("uncertain_difference")
            if len(comparison["evidence"]) > 1:
                concerns.append("multiple_comparisons")
            review = ReviewDecision(
                assessment="inconclusive"
                if "small_sample" in concerns or "uncertain_difference" in concerns
                else "relevant",
                concerns=concerns,
                evidence_ids=list(comparison["evidence"]),
            )
            if run["request"]["mode"] == "live":
                role = (
                    "independent methodological reviewer"
                    if run["request"]["workflow"] == "staged"
                    else "single research agent"
                )
                response = self.provider.request(
                    role,
                    dict(
                        question=run["request"]["question"],
                        plan=plan.model_dump(),
                        evidence=comparison,
                        deterministic_review=review.model_dump(),
                    ),
                    ReviewDecision,
                    ctx,
                )
                if not set(response.evidence_ids) <= set(comparison["evidence"]):
                    raise ValueError("Reviewer cited nonexistent evidence")
                review.concerns = sorted(set(review.concerns + response.concerns))
                if response.assessment != "relevant":
                    review.assessment = response.assessment
            self.store.update(rid, review=review.model_dump())
            self.store.artifact(rid, "review.json", review.model_dump_json())
            tools.call("generate_chart", {})
            tools.call(
                "save_research_report",
                dict(
                    claims=[
                        dict(evidence_id=e["id"], conclusion=e["conclusion"])
                        for e in comparison["evidence"].values()
                    ]
                ),
            )
            ctx.check()
            required = {
                "plan.json",
                "results.json",
                "results.csv",
                "comparison.json",
                "chart.svg",
                "chart-inputs.json",
                "report.md",
                "review.json",
            }
            if not required <= set(self.store.artifact_names(rid)):
                raise ValueError("Required artifact missing")
            self.store.event(
                rid,
                "validation",
                "All tasks, claims, numerical report and required artifacts validated",
            )
            self.store.artifact(rid, "logs.json", canonical(self.store.events(rid)))
            hashes = {
                n: hashlib.sha256(self.store.artifact_get(rid, n).encode()).hexdigest()
                for n in self.store.artifact_names(rid)
                if n != "evidence.json"
            }
            self.store.artifact(
                rid,
                "evidence.json",
                canonical(
                    dict(
                        source=run["source"],
                        plan=plan.model_dump(),
                        artifact_sha256=hashes,
                        mode=run["request"]["mode"],
                        workflow=run["request"]["workflow"],
                        usage={
                            k: self.store.get(rid)[k]
                            for k in (
                                "input_tokens",
                                "output_tokens",
                                "cost_usd",
                                "elapsed",
                                "work",
                                "tools",
                                "model_calls",
                            )
                        },
                        claims_validated=True,
                    )
                ),
            )
            self.state(rid, "completed")
        except StopRun as exc:
            self.store.update(rid, error=str(exc))
            self.state(rid, "canceled")
        except Exception as exc:
            # Uncontrolled exception bodies may contain provider inputs or secrets.
            message = (
                str(exc)
                if isinstance(exc, (ValueError, BudgetExceeded, ProviderError))
                and len(str(exc)) < 700
                else f"{type(exc).__name__}: task failed; inspect action log and retry from checkpoints"
            )
            self.store.update(rid, error=message)
            self.store.event(rid, "failure", message, error_type=type(exc).__name__)
            self.state(rid, "failed")
        finally:
            self.store.update(rid, elapsed=ctx.prior + time.monotonic() - ctx.started)
