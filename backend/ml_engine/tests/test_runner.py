"""Check the subprocess adapter without involving Django or a database."""

import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import joblib

from ml_engine.errors import DatasetValidationError
from ml_engine.runner import main, run_training


class RunnerTests(TestCase):
    def test_adapter_saves_all_models_and_records_input_schema(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "train.csv"
            source.write_text(
                "value,target\n"
                + "".join(f"{index},{index * 2}\n" for index in range(20))
            )
            summaries = run_training(
                {
                    "dataset_path": str(source),
                    "target_column": "target",
                    "task": "regression",
                    "algorithms": ["linear_regression"],
                    "output_directory": str(root),
                    "metadata": {"experiment_id": 1},
                }
            )
            self.assertEqual(len(summaries), 1)
            artifact = joblib.load(root / summaries[0]["filename"])
            self.assertEqual(
                artifact["metadata"]["experiment"]["feature_columns"], ["value"]
            )
            self.assertEqual(artifact["metadata"]["experiment"]["experiment_id"], 1)

    def test_cli_returns_json_on_success_and_domain_failure(self):
        for failure in (None, DatasetValidationError("Invalid target")):
            output = io.StringIO()
            with (
                patch("ml_engine.runner.sys.stdin", io.StringIO("{}")),
                patch("ml_engine.runner.sys.stdout", output),
                patch(
                    "ml_engine.runner.run_training",
                    return_value=[{"algorithm": "test"}],
                    side_effect=failure,
                ),
            ):
                code = main()
            self.assertEqual(code, int(failure is not None))
            payload = json.loads(output.getvalue())
            self.assertEqual(
                payload,
                {"error": "Invalid target"}
                if failure
                else {"results": [{"algorithm": "test"}]},
            )

    def test_cli_hides_internal_exception_details(self):
        output = io.StringIO()
        with (
            patch("ml_engine.runner.sys.stdin", io.StringIO("{}")),
            patch("ml_engine.runner.sys.stdout", output),
            patch(
                "ml_engine.runner.run_training",
                side_effect=RuntimeError("private path"),
            ),
            self.assertLogs("ml_engine.runner", level="ERROR"),
        ):
            self.assertEqual(main(), 1)
        self.assertNotIn("private path", output.getvalue())
