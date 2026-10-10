import json
from unittest import TestCase

from ml_engine.errors import TrainingError
from ml_engine.metrics import calculate_metrics, selection_score


class MetricsTests(TestCase):
    def test_classification_metrics_are_json_compatible(self):
        metrics = calculate_metrics(
            "classification", ["a", "a", "b", "b"], ["a", "b", "b", "b"]
        )

        self.assertAlmostEqual(metrics["accuracy"], 0.75)
        self.assertTrue(0 <= metrics["f1_macro"] <= 1)
        json.dumps(metrics, allow_nan=False)

    def test_regression_metrics_have_expected_values(self):
        metrics = calculate_metrics("regression", [1, 3, 5], [2, 3, 4])

        self.assertAlmostEqual(metrics["mae"], 2 / 3)
        self.assertAlmostEqual(metrics["rmse"], (2 / 3) ** 0.5)
        self.assertAlmostEqual(metrics["r2"], 0.75)
        json.dumps(metrics, allow_nan=False)

    def test_selection_maximizes_f1_and_minimizes_mae(self):
        self.assertGreater(
            selection_score("classification", {"f1_macro": 0.9}),
            selection_score("classification", {"f1_macro": 0.8}),
        )
        self.assertGreater(
            selection_score("regression", {"mae": 1.0}),
            selection_score("regression", {"mae": 5.0}),
        )

    def test_rejects_unknown_task(self):
        with self.assertRaises(TrainingError):
            calculate_metrics("unknown", [1, 2], [1, 2])
        with self.assertRaises(TrainingError):
            selection_score("unknown", {})
