from .models import ExperimentPlan, Parameters, PlanningDecision, Scenario

EXAMPLES = [
    "How does increased quote latency affect market-maker P&L and inventory risk?",
    "Does a tighter inventory limit reduce losses under more informed order flow?",
    "Which tested configuration has the best tradeoff between P&L and drawdown?",
    "How does higher volatility affect execution edge?",
    "How does a wider spread affect P&L?",
    "Where does the C++ matching implementation improve performance?",
]


def normalize(text):
    return " ".join(text.lower().strip().rstrip("?.!").split())


def offline_plan(question):
    lookup = {normalize(q): i for i, q in enumerate(EXAMPLES)}
    key = normalize(question)
    if key not in lookup:
        ambiguous = key in (
            "make it better",
            "what is the best strategy",
            "compare risk",
        )
        return PlanningDecision(
            outcome="clarify" if ambiguous else "unsupported",
            explanation="Offline planning is scripted. Select an exact example question. Supported controls: quote refresh, inventory limit, informed share, volatility, spread and inventory skew. No live prices, fees, options or brokerage tools.",
            plan=None,
        )
    i = lookup[key]
    base = Parameters()
    variants = [("slow_quotes", {"quote_refresh_interval": 5})]
    if i == 1:
        base = Parameters(informed_share=0.7)
        variants = [("tight_inventory", {"max_inventory": 20})]
    elif i == 2:
        variants = [
            ("tight_inventory", {"max_inventory": 20}),
            ("wide_spread", {"half_spread_ticks": 6}),
        ]
    elif i == 3:
        variants = [("volatile", {"volatility_ticks": 10})]
    elif i == 4:
        variants = [("wide_spread", {"half_spread_ticks": 6})]
    elif i == 5:
        variants = [("cpp", {})]
    seeds = [17, 42, 73, 101, 137, 211]
    plan = ExperimentPlan(
        hypothesis=question,
        kind="matching_benchmark" if i == 5 else "simulation",
        baseline=base,
        treatments=[
            Scenario(name=n, parameters=Parameters(**{**base.model_dump(), **p}))
            for n, p in variants
        ],
        steps=500,
        seeds=seeds,
        estimated_work=500 * len(seeds) * (1 + len(variants)),
        assumptions=[
            "Synthetic market; no real-world trading inference.",
            "Simulation configurations use disjoint deterministic seed schedules; no common-random-number claim.",
            "Exploratory unpaired normal-approximation intervals; no strong ranking from overlapping or small samples.",
        ],
    )
    return PlanningDecision(
        outcome="planned",
        explanation="Scripted planner selected a supported experiment. Deterministic validation runs before any work.",
        plan=plan,
    )


def describe():
    return {
        "parameters": Parameters.model_json_schema(),
        "examples": EXAMPLES,
        "fixed": {"initial_fair_value_ticks": 10000, "simulation_backend": "python"},
        "limits": {"steps": [20, 2000], "seeds": [2, 12], "treatments": [1, 3]},
        "methods": "Disjoint seed offsets 100000 × scenario index for simulations. Benchmarks share identical prepared workloads and verify parity. No external data or arbitrary tools.",
    }
