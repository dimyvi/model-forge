import json
from unittest import TestCase
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator
from sklearn.model_selection import train_test_split

from ml_engine.errors import (
    AlgorithmValidationError,
    DatasetValidationError,
    TrainingError,
)
from ml_engine.metrics import calculate_metrics, selection_score
from ml_engine.training import train_experiment


def classification_data():
    return pd.DataFrame(
        {
            "value": np.arange(80, dtype=float),
            "city": pd.Series(
                ["Montréal", "Zürich", None, "Tokyo"] * 20, dtype="string"
            ),
            "target": ["low"] * 40 + ["high"] * 40,
        }
    )


def regression_data():
    values = np.arange(60, dtype=float)
    return pd.DataFrame({"value": values, "target": values * 2 + 3})


class FailingEstimator(BaseEstimator):
    def fit(self, features, target):
        raise ValueError("Unsupported input")


class TrainingTests(TestCase):
    def test_classification_uses_existing_algorithm_ids_and_one_best_result(self):
        data = classification_data()
        before = data.copy(deep=True)

        results = train_experiment(
            data, "target", "classification", ["logistic_regression", "random_forest"]
        )

        self.assertEqual(
            [result.algorithm for result in results],
            ["logistic_regression", "random_forest"],
        )
        self.assertEqual(sum(result.is_best for result in results), 1)
        best = next(result for result in results if result.is_best)
        self.assertEqual(
            selection_score("classification", best.metrics),
            max(
                selection_score("classification", result.metrics) for result in results
            ),
        )
        for result in results:
            self.assertEqual(set(result.metrics), {"accuracy", "f1_macro"})
            self.assertNotIn("target", result.model.feature_names_in_)
            json.dumps(result.metrics, allow_nan=False)
        pd.testing.assert_frame_equal(data, before)

    def test_regression_uses_lowest_mae(self):
        results = train_experiment(
            regression_data(),
            "target",
            "regression",
            ["linear_regression", "random_forest"],
        )

        best = next(result for result in results if result.is_best)
        self.assertEqual(best.algorithm, "linear_regression")
        self.assertAlmostEqual(best.metrics["r2"], 1.0)
        self.assertEqual(set(best.metrics), {"mae", "rmse", "r2"})

    def test_preprocessing_is_fitted_only_on_training_rows(self):
        data = regression_data()
        data.loc[0, "value"] = 10_000.0
        features = data.drop(columns="target")
        x_train, x_validation, _, y_validation = train_test_split(
            features, data["target"], test_size=0.25, random_state=42
        )

        result = train_experiment(data, "target", "regression", ["linear_regression"])[
            0
        ]

        numeric = result.model.named_steps["preprocessor"].named_transformers_[
            "numeric"
        ]
        self.assertAlmostEqual(
            numeric.named_steps["scaler"].mean_[0], x_train["value"].mean()
        )
        self.assertNotEqual(
            numeric.named_steps["scaler"].mean_[0], data["value"].mean()
        )
        self.assertEqual(
            result.metrics,
            calculate_metrics(
                "regression", y_validation, result.model.predict(x_validation)
            ),
        )

    def test_seed_makes_result_reproducible(self):
        first = train_experiment(
            classification_data(),
            "target",
            "classification",
            ["random_forest"],
            random_state=7,
        )[0]
        second = train_experiment(
            classification_data(),
            "target",
            "classification",
            ["random_forest"],
            random_state=7,
        )[0]

        self.assertEqual(first.metrics, second.metrics)
        np.testing.assert_array_equal(
            first.model.predict(classification_data().drop(columns="target")),
            second.model.predict(classification_data().drop(columns="target")),
        )

    def test_rejects_invalid_split_or_seed(self):
        for fraction in (0, 1, True, "0.25", float("nan")):
            with self.subTest(fraction=fraction), self.assertRaises(TrainingError):
                train_experiment(
                    regression_data(),
                    "target",
                    "regression",
                    ["linear_regression"],
                    validation_size=fraction,
                )
        for seed in (-1, True, 2**32, 0.5):
            with self.subTest(seed=seed), self.assertRaises(TrainingError):
                train_experiment(
                    regression_data(),
                    "target",
                    "regression",
                    ["linear_regression"],
                    random_state=seed,
                )

    def test_rejects_one_class_and_singleton_class(self):
        for target in (["one"] * 80, ["major"] * 79 + ["rare"]):
            data = classification_data().assign(target=target)
            with (
                self.subTest(target=target[-1]),
                self.assertRaises(DatasetValidationError),
            ):
                train_experiment(
                    data, "target", "classification", ["logistic_regression"]
                )

    def test_rejects_continuous_classification_target(self):
        data = classification_data().assign(target=np.arange(80) / 10)

        with self.assertRaises(DatasetValidationError):
            train_experiment(data, "target", "classification", ["random_forest"])

    def test_rejects_text_bool_and_constant_regression_target(self):
        for target in (["a", "b"] * 30, [True, False] * 30, [1.0] * 60):
            data = regression_data().assign(target=target)
            with (
                self.subTest(target=target[0]),
                self.assertRaises(DatasetValidationError),
            ):
                train_experiment(data, "target", "regression", ["linear_regression"])

    def test_rejects_too_small_holdout_and_incompatible_algorithm(self):
        data = classification_data().iloc[:4].copy()
        data["target"] = ["a", "a", "b", "b"]
        with self.assertRaises(DatasetValidationError):
            train_experiment(data, "target", "classification", ["random_forest"])
        with self.assertRaises(AlgorithmValidationError):
            train_experiment(
                classification_data(), "target", "classification", ["linear_regression"]
            )

    def test_wraps_training_failure_in_domain_error(self):
        with (
            patch(
                "ml_engine.training.create_algorithms",
                return_value={"broken": FailingEstimator()},
            ),
            self.assertRaisesRegex(TrainingError, "broken"),
        ):
            train_experiment(regression_data(), "target", "regression", ["broken"])
