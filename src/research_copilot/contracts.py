"""Server-owned response contracts, exported to the React client by OpenAPI."""

from typing import Any, Literal
from pydantic import BaseModel, Field
from .models import ExperimentPlan, ReviewDecision, StartRequest

State = Literal[
    "draft",
    "planning",
    "validated",
    "running",
    "reviewing",
    "completed",
    "failed",
    "canceled",
    "interrupted",
]


class RunSummary(BaseModel):
    id: str
    question: str
    state: State
    created: float
    mode: Literal["offline", "live"]


class ActionEvent(BaseModel):
    seq: int
    time: float
    kind: str
    summary: str
    ok: bool | None = None
    duration_ms: float | None = None
    args: dict[str, Any] | None = None
    error: str | None = None
    error_type: str | None = None
    model: str | None = None
    usage: dict[str, int] | None = None


class RunView(BaseModel):
    id: str
    audience: Literal["public_demo"] | None = None
    revision: int = 0
    request: StartRequest
    source: dict[str, Any]
    state: State
    plan: ExperimentPlan | None
    created: float
    elapsed: float
    explanation: str
    completed_tasks: int
    work: int
    tools: int
    model_calls: int
    output_reserved: int
    input_tokens: int | None
    output_tokens: int | None
    usage_complete: bool = False
    cost_usd: float | None
    cancel_requested: bool
    review: ReviewDecision | None
    error: str | None
    failure_code: str | None = None
    decision_outcome: Literal["planned", "unsupported", "clarify"] | None = None
    resume_count: int = 0
    can_resume: bool = False
    next_action: str = ""
    events: list[ActionEvent] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)


class Capabilities(BaseModel):
    parameters: dict[str, Any]
    examples: list[str]
    fixed: dict[str, Any]
    limits: dict[str, Any]
    methods: str
    public_demo: bool
    live_configured: bool
    live_verification: str
    tool_schemas: dict[str, Any]
