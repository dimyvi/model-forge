from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd

from ml_engine.artifacts import save_model
from ml_engine.errors import ArtifactError
from ml_engine.training import train_experiment


class ArtifactTests(TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        values = np.arange(20, dtype=float)
        data = pd.DataFrame(
            {
                "value": values,
                "city": pd.Series(["a", "b", pd.NA, ""] * 5, dtype="string"),
                "target": values * 2,
            }
        )
        self.result = train_experiment(
            data, "target", "regression", ["linear_regression"]
        )[0]

    def test_saved_artifact_restores_full_pipeline_and_metadata(self):
        path = self.directory / "models" / "trained.joblib"
        metadata = {
            "task": "regression",
            "target_column": "target",
            "metrics": self.result.metrics,
        }

        returned_path = save_model(self.result.model, path, metadata=metadata)
        artifact = joblib.load(returned_path)

        self.assertEqual(returned_path, path)
        self.assertEqual(artifact["schema_version"], 1)
        self.assertEqual(artifact["metadata"]["experiment"], metadata)
        self.assertIn("scikit-learn", artifact["metadata"]["library_versions"])
        new_data = pd.DataFrame(
            {"value": [2.0, 3.0], "city": pd.Series(["new", pd.NA], dtype="string")}
        )
        np.testing.assert_allclose(
            artifact["pipeline"].predict(new_data), self.result.model.predict(new_data)
        )

    def test_rejects_wrong_file_extension_and_invalid_metadata(self):
        with self.assertRaises(ArtifactError):
            save_model(self.result.model, self.directory / "model.txt")
        for metadata in ({"value": object()}, {"value": float("nan")}):
            with self.subTest(metadata=metadata), self.assertRaises(ArtifactError):
                save_model(
                    self.result.model,
                    self.directory / "model.joblib",
                    metadata=metadata,
                )

    def test_rejects_estimator_without_pipeline_and_unfitted_pipeline(self):
        from sklearn.linear_model import LinearRegression
        from sklearn.pipeline import Pipeline

        for model in (LinearRegression(), Pipeline([("model", LinearRegression())])):
            with self.subTest(model=model), self.assertRaises(ArtifactError):
                save_model(model, self.directory / "model.joblib")

    def test_failed_write_keeps_existing_artifact_and_cleans_temporary_file(self):
        path = self.directory / "model.joblib"
        path.write_bytes(b"existing artifact")

        with (
            patch("ml_engine.artifacts.joblib.dump", side_effect=OSError("Disk full")),
            self.assertRaises(ArtifactError),
        ):
            save_model(self.result.model, path)

        self.assertEqual(path.read_bytes(), b"existing artifact")
        self.assertEqual(list(self.directory.iterdir()), [path])
