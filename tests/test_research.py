import tempfile
import unittest
from pathlib import Path

from orderbook.market_lab import SimulationConfig
from orderbook.research import (
    mean_confidence_interval,
    run_scenario_study,
    write_dict_rows,
)


class ResearchTests(unittest.TestCase):
    def test_confidence_interval_contains_mean(self):
        mean, low, high = mean_confidence_interval([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(mean, 2.5)
        self.assertLess(low, mean)
        self.assertGreater(high, mean)

    def test_study_runs_common_seeds(self):
        scenarios = {
            "base": SimulationConfig(steps=20),
            "informed": SimulationConfig(steps=20, informed_share=0.8),
        }
        runs, summary = run_scenario_study(scenarios, seeds=[1, 2, 3])
        self.assertEqual(len(runs), 6)
        self.assertEqual(len(summary), 2)
        self.assertTrue(all(row["runs"] == 3 for row in summary))

    def test_pnl_decomposition_reconciles(self):
        runs, _ = run_scenario_study({"base": SimulationConfig(steps=30)}, seeds=[1, 2])
        for row in runs:
            decomposed = (
                row["execution_edge_pnl_ticks"] + row["inventory_revaluation_pnl_ticks"]
            )
            self.assertEqual(row["ending_pnl_ticks"], decomposed)

    def test_csv_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "study.csv"
            write_dict_rows(path, [{"scenario": "base", "value": 1}])
            self.assertIn("scenario,value", path.read_text(encoding="utf-8"))

    def test_rejects_too_few_observations(self):
        with self.assertRaises(ValueError):
            mean_confidence_interval([1.0])
        with self.assertRaises(ValueError):
            run_scenario_study({"base": SimulationConfig()}, seeds=[1])


if __name__ == "__main__":
    unittest.main()
