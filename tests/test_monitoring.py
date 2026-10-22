
"""Tests du monitoring."""
import unittest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tiktok_history_factory.monitoring.metrics import MetricsCollector, PhaseMetrics
from tiktok_history_factory.monitoring.costs import CostEstimate
from tiktok_history_factory.monitoring.logs import StructuredLogger


class TestMetrics(unittest.TestCase):
    def test_phase_duration(self):
        """La duree d'une phase est positive."""
        import time
        collector = MetricsCollector()
        phase = collector.start_phase("test")
        time.sleep(0.01)
        collector.end_phase("test", success=True)
        self.assertGreater(phase.duration_ms, 0)

    def test_summary_counts(self):
        """Le resume compte correctement."""
        collector = MetricsCollector()
        collector.start_phase("p1")
        collector.end_phase("p1", success=True)
        collector.start_phase("p2")
        collector.end_phase("p2", success=False)
        summary = collector.summary()
        self.assertEqual(summary["phases_count"], 2)
        self.assertEqual(summary["success_count"], 1)
        self.assertEqual(summary["failed_count"], 1)


class TestCosts(unittest.TestCase):
    def test_electricity_calculation(self):
        """Le calcul de l'electricite est correct."""
        cost = CostEstimate(gpu_compute_time_hours=1.0, gpu_power_watts=120.0, kwh_price=0.20)
        result = cost.calculate()
        self.assertAlmostEqual(result["kwh"], 0.12, places=4)
        self.assertAlmostEqual(result["electricity_eur"], 0.024, places=4)


class TestLogs(unittest.TestCase):
    def test_log_event(self):
        """Un evenement est loggue."""
        with tempfile.TemporaryDirectory() as td:
            logger = StructuredLogger(log_dir=td)
            entry = logger.log_event("test_event", task_id=1, phase="test")
            self.assertEqual(entry["event_type"], "test_event")
            self.assertEqual(entry["task_id"], 1)


if __name__ == "__main__":
    unittest.main()
