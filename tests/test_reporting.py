"""Check recorded-data reporting and prevent incomparable study aggregation."""

import copy
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


compare, study = load("compare"), load("study")


def dataset(seed=17):
    # Deliberately skewed samples distinguish the median from a mean/best trial.
    return dict(
        seed=seed,
        count=100,
        repeats=3,
        workloads=["crossing"],
        backends=["python", "cpp"],
        source_sha256="same",
        environment={"platform": "recorded host", "python": "recorded version"},
        runs=[
            dict(
                workload="crossing",
                backend=b,
                trial=i,
                events_per_second=rate,
                p50_us=1,
                p95_us=2,
                p99_us=3,
            )
            for b, rates in [("python", [10, 20, 900]), ("cpp", [30, 60, 800])]
            for i, rate in enumerate(rates)
        ],
    )


def test_nearest_rank_quantiles():
    assert compare.percentile([4000, 1000, 3000, 2000], 0.5) == 2
    assert compare.percentile([4000, 1000, 3000, 2000], 0.99) == 4


def test_report_uses_saved_environment_and_all_trials(tmp_path):
    compare.report(dataset(), tmp_path, chart=False)
    text = (tmp_path / "SUMMARY.md").read_text()
    assert "recorded host" in text and "recorded version" in text
    assert "| crossing | python | 20 | 10–900 |" in text
    assert b"\r\n" not in (tmp_path / "results.csv").read_bytes()


def test_study_uses_ratio_of_medians():
    result = study.summarize([dataset(17), dataset(42)])
    assert [r["speedup"] for r in result["rows"]] == [3, 3]


@pytest.mark.parametrize(
    "failure", ["source", "environment", "count", "missing_trial", "duplicate_seed"]
)
def test_study_rejects_incomparable_inputs(failure):
    a, b = dataset(), copy.deepcopy(dataset(42))
    if failure == "source":
        b["source_sha256"] = "different"
    elif failure == "environment":
        b["environment"]["platform"] = "other"
    elif failure == "count":
        b["count"] += 1
    elif failure == "missing_trial":
        b["runs"].pop()
    else:
        b["seed"] = a["seed"]
    with pytest.raises(ValueError):
        study.summarize([a, b])
