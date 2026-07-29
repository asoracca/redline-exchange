import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from orderbook.market_lab import SimulationConfig, run_market_simulation


class MarketLabTests(unittest.TestCase):
    def test_seed_makes_simulation_reproducible(self):
        config = SimulationConfig(steps=100, seed=11)
        first = run_market_simulation(config)
        second = run_market_simulation(config)
        self.assertEqual(first.records, second.records)
        self.assertEqual(first.summary(), second.summary())

    def test_inventory_limit_is_respected(self):
        config = SimulationConfig(steps=500, seed=4, max_inventory=20)
        result = run_market_simulation(config)
        self.assertLessEqual(result.summary()["max_abs_inventory"], 20)

    def test_slow_quotes_are_a_distinct_experiment(self):
        baseline = SimulationConfig(steps=300, seed=21)
        slow = replace(baseline, quote_refresh_interval=5)
        baseline_result = run_market_simulation(baseline)
        slow_result = run_market_simulation(slow)
        self.assertNotEqual(baseline_result.records, slow_result.records)
        self.assertEqual(len(slow_result.records), 300)

    def test_informed_volume_is_reported(self):
        config = SimulationConfig(
            steps=500,
            seed=8,
            informed_share=1.0,
            volatility_ticks=10,
        )
        summary = run_market_simulation(config).summary()
        self.assertGreater(summary["volume"], 0)
        self.assertEqual(summary["informed_volume_share"], 1.0)

    def test_records_can_be_exported(self):
        result = run_market_simulation(SimulationConfig(steps=5))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "records.csv"
            result.write_records_csv(path)
            self.assertTrue(path.exists())
            self.assertEqual(len(path.read_text(encoding="utf-8").splitlines()), 6)

    def test_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            SimulationConfig(steps=0)
        with self.assertRaises(ValueError):
            SimulationConfig(informed_share=1.1)


if __name__ == "__main__":
    unittest.main()
