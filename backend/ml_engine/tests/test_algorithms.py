from unittest import TestCase

from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

from ml_engine.algorithms import available_algorithms, create_algorithms
from ml_engine.errors import AlgorithmValidationError


class AlgorithmRegistryTests(TestCase):
    def test_classification_ids_match_existing_frontend(self):
        self.assertEqual(
            set(available_algorithms("classification")),
            {"logistic_regression", "random_forest"},
        )

    def test_same_forest_id_creates_task_specific_estimator(self):
        classifier = create_algorithms("classification", ["random_forest"])[
            "random_forest"
        ]
        regressor = create_algorithms("regression", ["random_forest"])["random_forest"]

        self.assertIsInstance(classifier, RandomForestClassifier)
        self.assertIsInstance(regressor, RandomForestRegressor)

    def test_each_call_creates_fresh_seeded_models(self):
        first = create_algorithms("classification", ["random_forest"], random_state=7)
        second = create_algorithms("classification", ["random_forest"], random_state=7)

        self.assertIsNot(first["random_forest"], second["random_forest"])
        self.assertEqual(first["random_forest"].random_state, 7)

    def test_rejects_unknown_task(self):
        for task in ("clustering", None, []):
            with self.subTest(task=task), self.assertRaises(AlgorithmValidationError):
                available_algorithms(task)

    def test_rejects_empty_repeated_or_malformed_selection(self):
        for selection in (
            [],
            "random_forest",
            None,
            [None],
            [{}],
            ["random_forest", "random_forest"],
        ):
            with (
                self.subTest(selection=selection),
                self.assertRaises(AlgorithmValidationError),
            ):
                create_algorithms("classification", selection)

    def test_rejects_algorithm_for_wrong_task(self):
        with self.assertRaises(AlgorithmValidationError):
            create_algorithms("classification", ["linear_regression"])
