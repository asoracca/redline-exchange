from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Parameters(StrictModel):
    volatility_ticks: int = Field(4, strict=True, ge=0, le=20)
    half_spread_ticks: int = Field(3, strict=True, ge=1, le=20)
    order_quantity: int = Field(10, strict=True, ge=1, le=20)
    informed_share: float = Field(0.25, ge=0, le=1, allow_inf_nan=False)
    inventory_skew: float = Field(0.05, ge=0, le=0.5, allow_inf_nan=False)
    max_inventory: int = Field(100, strict=True, ge=10, le=200)
    quote_refresh_interval: int = Field(1, strict=True, ge=1, le=20)

    @model_validator(mode="after")
    def inventory(self):
        if self.max_inventory < self.order_quantity:
            raise ValueError("Inventory limit must cover one order")
        return self


class Scenario(StrictModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,30}$")
    parameters: Parameters


METRICS = (
    "ending_pnl_ticks",
    "max_abs_inventory",
    "max_drawdown_ticks",
    "execution_edge_pnl_ticks",
    "inventory_revaluation_pnl_ticks",
)
Metric = Literal[
    "ending_pnl_ticks",
    "max_abs_inventory",
    "max_drawdown_ticks",
    "execution_edge_pnl_ticks",
    "inventory_revaluation_pnl_ticks",
]


class ExperimentPlan(StrictModel):
    hypothesis: str = Field(min_length=5, max_length=500)
    kind: Literal["simulation", "matching_benchmark"] = "simulation"
    baseline: Parameters = Field(default_factory=Parameters)
    treatments: list[Scenario] = Field(min_length=1, max_length=3)
    steps: int = Field(500, strict=True, ge=20, le=2000)
    seeds: list[Annotated[int, Field(strict=True, ge=0, le=99999)]] = Field(
        min_length=2, max_length=12
    )
    metrics: list[Metric] = Field(
        default_factory=lambda: list(METRICS), min_length=1, max_length=5
    )
    workload: Literal["crossing", "resting", "cancel_replace", "mixed"] = "mixed"
    estimated_work: int = Field(strict=True, ge=1, le=100000)
    assumptions: list[Annotated[str, Field(max_length=500)]] = Field(
        min_length=1, max_length=8
    )

    @model_validator(mode="after")
    def valid(self):
        if len(set(self.seeds)) != len(self.seeds):
            raise ValueError("Seeds must be unique")
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("Metrics must be unique")
        names = [x.name for x in self.treatments]
        if len(set(names)) != len(names) or "baseline" in names:
            raise ValueError("Treatment names must be unique and not baseline")
        if self.estimated_work != self.steps * len(self.seeds) * (
            1 + len(self.treatments)
        ):
            raise ValueError("Estimated work must equal steps × seeds × configurations")
        if self.kind == "matching_benchmark" and (
            names != ["cpp"]
            or self.baseline != Parameters()
            or self.treatments[0].parameters != Parameters()
        ):
            raise ValueError(
                "Benchmark uses fixed Python/C++ backends and workload, not simulation parameters"
            )
        return self


class Limits(StrictModel):
    max_work: int = Field(40000, strict=True, ge=40, le=100000)
    max_tools: int = Field(100, strict=True, ge=1, le=160)
    max_model_calls: int = Field(4, strict=True, ge=1, le=6)
    max_output_tokens: int = Field(6000, strict=True, ge=256, le=12000)
    max_seconds: int = Field(120, strict=True, ge=1, le=300)


class StartRequest(StrictModel):
    question: str = Field(min_length=5, max_length=1500)
    mode: Literal["offline", "live"] = "offline"
    workflow: Literal["staged", "single_agent"] = "staged"
    limits: Limits = Field(default_factory=Limits)


class PlanningDecision(StrictModel):
    outcome: Literal["planned", "unsupported", "clarify"]
    explanation: str = Field(max_length=600)
    plan: ExperimentPlan | None

    @model_validator(mode="after")
    def consistent(self):
        if (self.outcome == "planned") != (self.plan is not None):
            raise ValueError("Only a planned decision must include a plan")
        return self


class ReviewDecision(StrictModel):
    assessment: Literal["relevant", "inconclusive", "question_mismatch"]
    concerns: list[
        Literal[
            "small_sample",
            "uncertain_difference",
            "multiple_comparisons",
            "synthetic_only",
            "question_mismatch",
        ]
    ]
    evidence_ids: list[Annotated[str, Field(max_length=100)]] = Field(max_length=20)


class EmptyArgs(StrictModel):
    pass


class TaskArgs(StrictModel):
    scenario: int = Field(strict=True, ge=0, le=3)
    seed_index: int = Field(strict=True, ge=0, le=11)


class Claim(StrictModel):
    evidence_id: str = Field(max_length=100)
    conclusion: Literal["positive", "negative", "inconclusive"]


class ReportArgs(StrictModel):
    claims: list[Claim] = Field(min_length=1, max_length=30)
