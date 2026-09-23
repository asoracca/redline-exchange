"""Closed tool registry: validated arguments, fixed artifact names, no code execution."""

import time
from .models import EmptyArgs, ExperimentPlan, TaskArgs, ReportArgs
from .planner import describe
from . import experiments
from .storage import canonical, digest

SCHEMAS = {
    "describe_simulator": EmptyArgs,
    "validate_experiment": ExperimentPlan,
    "run_simulation_batch": TaskArgs,
    "run_matching_benchmark": TaskArgs,
    "load_run_results": EmptyArgs,
    "compare_experiments": EmptyArgs,
    "generate_chart": EmptyArgs,
    "save_research_report": ReportArgs,
}


class Registry:
    def __init__(self, context):
        self.ctx = context
        self.store = context.store
        self.rid = context.rid

    def call(self, name, args):
        start = time.monotonic()
        try:
            self.ctx.check()
            self.ctx.reserve("tools", 1, "max_tools")
            if name not in SCHEMAS:
                raise ValueError("Tool not authorized")
            parsed = SCHEMAS[name].model_validate(args)
            result = self._execute(name, parsed)
            self.ctx.check()
            self.store.event(
                self.rid,
                "tool",
                name,
                args=args,
                duration_ms=round((time.monotonic() - start) * 1000, 3),
                ok=True,
            )
            return result
        except Exception as exc:
            # Errors describe controlled validation, never echo provider responses.
            self.store.event(
                self.rid,
                "tool",
                name,
                args=args,
                duration_ms=round((time.monotonic() - start) * 1000, 3),
                ok=False,
                error=type(exc).__name__,
            )
            raise

    def _execute(self, name, args):
        run = self.store.get(self.rid)
        if name == "describe_simulator":
            return describe()
        if name == "validate_experiment":
            if run["plan"] is not None or run["state"] != "draft":
                raise ValueError("Validated plans are immutable")
            if args.estimated_work > run["request"]["limits"]["max_work"]:
                raise ValueError("Plan exceeds computational budget; no tasks started")
            if args.kind == "matching_benchmark":
                from orderbook.native import NativeLimitOrderBook

                NativeLimitOrderBook("CHECK")
            self.store.update(self.rid, plan=args.model_dump())
            self.store.artifact(self.rid, "plan.json", canonical(args.model_dump()))
            return args
        if not run["plan"]:
            raise ValueError("A validated plan is required")
        plan = ExperimentPlan.model_validate(run["plan"])
        if name in ("run_simulation_batch", "run_matching_benchmark"):
            if name != (
                "run_simulation_batch"
                if plan.kind == "simulation"
                else "run_matching_benchmark"
            ):
                raise ValueError("Tool does not match plan kind")
            if args.scenario > len(plan.treatments) or args.seed_index >= len(
                plan.seeds
            ):
                raise ValueError("Task outside validated schedule")
            key = f"{args.scenario}:{args.seed_index}"
            existing = self.store.task(self.rid, key)
            if existing:
                return experiments.validate_result(
                    plan, args.scenario, args.seed_index, existing
                )
            cachekey = digest(
                dict(
                    source=run["source"],
                    plan=run["plan"],
                    scenario=args.scenario,
                    seed_index=args.seed_index,
                )
            )
            result = (
                self.store.cache_get(cachekey) if plan.kind == "simulation" else None
            )
            self.ctx.reserve("work", plan.steps, "max_work")
            if result is None:
                result = experiments.execute(plan, args.scenario, args.seed_index)
            else:
                self.store.event(
                    self.rid, "cache", "Reused deterministic task", task=key
                )
            experiments.validate_result(plan, args.scenario, args.seed_index, result)
            self.store.save_task(
                self.rid, key, result, cachekey if plan.kind == "simulation" else None
            )
            self.store.update(self.rid, completed_tasks=len(self.store.tasks(self.rid)))
            return result
        rows = self.store.tasks(self.rid)
        for row in rows:
            i, j = map(int, row["key"].split(":"))
            experiments.validate_result(plan, i, j, row)
        if name == "load_run_results":
            self.store.artifact(self.rid, "results.json", canonical(rows))
            self.store.artifact(self.rid, "results.csv", experiments.csv_results(rows))
            return rows
        comparison = experiments.compare(plan, rows)
        if name == "compare_experiments":
            self.store.artifact(self.rid, "comparison.json", canonical(comparison))
            return comparison
        if name == "generate_chart":
            self.store.artifact(
                self.rid, "chart-inputs.json", canonical(comparison["groups"])
            )
            self.store.artifact(self.rid, "chart.svg", experiments.chart(comparison))
            return "chart.svg"
        if name == "save_research_report":
            if not run["review"]:
                raise ValueError("Review required before report")
            report = experiments.render_report(
                plan, comparison, args.claims, run["review"]
            )
            self.store.artifact(self.rid, "report.md", report)
            return "report.md"
        raise ValueError("Tool not authorized")
