"""Exercise the HTTP/queue/worker/download lifecycle with real ML artifacts."""

import subprocess
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import joblib
import pandas as pd
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APITransactionTestCase

from datasets.models import Dataset
from experiments.models import Experiment, ExperimentResult
from experiments.worker import (
    claim_next_experiment,
    execute_experiment,
    publish_results,
    recover_stale_jobs,
)


class TrainingApiTests(APITransactionTestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.media = Path(directory.name)
        settings_override = override_settings(MEDIA_ROOT=directory.name)
        settings_override.enable()
        self.addCleanup(settings_override.disable)
        self.user = User.objects.create_user(
            username="trainer", password="training-pass-123"
        )
        self.other_user = User.objects.create_user(
            username="other-trainer", password="training-pass-123"
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")
        rows = "\n".join(
            f"{index},{'a' if index < 12 else 'b'},{index * 2}" for index in range(24)
        )
        self.dataset = Dataset.objects.create(
            owner=self.user,
            file=SimpleUploadedFile(
                "train.csv", f"value,label,price\n{rows}\n".encode()
            ),
        )

    def create_experiment(self, **overrides):
        values = {
            "dataset": self.dataset.pk,
            "task": "classification",
            "target_column": "label",
            "algorithms": ["logistic_regression", "random_forest"],
            **overrides,
        }
        response = self.client.post(
            reverse("experiment-list-create"), values, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        return Experiment.objects.get(pk=response.data["id"])

    def start(self, experiment):
        return self.client.post(
            reverse("experiment-start", args=[experiment.pk]), {}, format="json"
        )

    def complete(self, experiment):
        self.assertEqual(self.start(experiment).status_code, 202)
        call_command("run_ml_worker", once=True, verbosity=0)
        experiment.refresh_from_db()
        self.assertEqual(experiment.status, "completed", experiment.error_message)

    def test_start_enqueues_without_training_and_rejects_duplicate_requests(self):
        experiment = self.create_experiment()
        with patch("experiments.worker.subprocess.run") as training:
            response = self.start(experiment)
            duplicate = self.start(experiment)
        training.assert_not_called()
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.data["status"], "queued")
        self.assertIsNotNone(response.data["queued_at"])
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(experiment.results.count(), 0)

    def test_classification_trains_downloads_and_restores_pipeline(self):
        experiment = self.create_experiment()
        self.complete(experiment)
        self.assertIsNotNone(experiment.started_at)
        self.assertIsNotNone(experiment.finished_at)
        response = self.client.get(reverse("experiment-detail", args=[experiment.pk]))
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(sum(item["is_best"] for item in response.data["results"]), 1)
        for summary in response.data["results"]:
            self.assertEqual(set(summary["metrics"]), {"accuracy", "f1_macro"})
            download = self.client.get(summary["model_file"])
            self.assertEqual(download.status_code, 200)
            result = experiment.results.get(pk=summary["id"])
            self.assertEqual(
                b"".join(download.streaming_content),
                Path(result.model_file.path).read_bytes(),
            )
            download.close()
            self.assertIn("attachment;", download["Content-Disposition"])
            artifact = joblib.load(result.model_file.path)
            self.assertEqual(
                artifact["metadata"]["experiment"]["experiment_id"], experiment.pk
            )
            self.assertEqual(
                artifact["metadata"]["experiment"]["feature_columns"],
                ["value", "price"],
            )
            self.assertEqual(
                len(
                    artifact["pipeline"].predict(
                        pd.DataFrame({"value": [3], "price": [6]})
                    )
                ),
                1,
            )
            self.assertTrue(
                result.model_file.name.startswith(
                    f"artifacts/user_{self.user.pk}/experiment_{experiment.pk}/"
                )
            )
        self.assertEqual(self.start(experiment).status_code, 409)

    def test_regression_trains_with_numeric_metrics(self):
        experiment = self.create_experiment(
            task="regression",
            target_column="price",
            algorithms=["linear_regression", "random_forest"],
        )
        self.complete(experiment)
        best = experiment.results.get(is_best=True)
        self.assertEqual(set(best.metrics), {"mae", "rmse", "r2"})
        self.assertEqual(best.algorithm, "linear_regression")

    def test_start_and_download_require_authentication_and_ownership(self):
        experiment = self.create_experiment()
        self.complete(experiment)
        result = experiment.results.first()
        download_url = reverse(
            "experiment-model-download", args=[experiment.pk, result.pk]
        )
        self.client.credentials()
        self.assertEqual(self.start(experiment).status_code, 401)
        self.assertEqual(self.client.get(download_url).status_code, 401)
        other_token = Token.objects.create(user=self.other_user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {other_token.key}")
        self.assertEqual(self.start(experiment).status_code, 404)
        self.assertEqual(self.client.get(download_url).status_code, 404)
        self.assertEqual(
            self.client.get(f"/media/{result.model_file.name}").status_code, 404
        )

    def test_model_download_rejects_missing_file_or_mismatched_experiment(self):
        experiment = self.create_experiment()
        experiment.status = "completed"
        experiment.save()
        result = ExperimentResult.objects.create(
            experiment=experiment,
            algorithm="random_forest",
            model_file="artifacts/missing.joblib",
        )
        self.assertEqual(
            self.client.get(
                reverse("experiment-model-download", args=[experiment.pk, result.pk])
            ).status_code,
            404,
        )
        other = self.create_experiment()
        self.assertEqual(
            self.client.get(
                reverse("experiment-model-download", args=[other.pk, result.pk])
            ).status_code,
            404,
        )

    def test_worker_failure_is_visible_without_partial_results_and_allows_retry(self):
        self.dataset.file.save(
            "invalid.csv", ContentFile(b"value,label,price\n1,,2\n2,a,4\n")
        )
        experiment = self.create_experiment()
        self.assertEqual(self.start(experiment).status_code, 202)
        call_command("run_ml_worker", once=True, verbosity=0)
        experiment.refresh_from_db()
        self.assertEqual(experiment.status, "failed")
        self.assertIn("missing values", experiment.error_message)
        self.assertEqual(experiment.results.count(), 0)
        old_run = experiment.run_id
        self.assertEqual(self.start(experiment).status_code, 202)
        experiment.refresh_from_db()
        self.assertNotEqual(experiment.run_id, old_run)
        self.assertEqual(experiment.error_message, "")

    def test_active_jobs_cannot_be_edited_or_deleted_or_lose_the_dataset(self):
        experiment = self.create_experiment()
        self.start(experiment)
        for current_status in ("queued", "running"):
            experiment.status = current_status
            experiment.save()
            self.assertEqual(
                self.client.patch(
                    reverse("experiment-detail", args=[experiment.pk]),
                    {"target_column": "label"},
                    format="json",
                ).status_code,
                400,
            )
            self.assertEqual(
                self.client.delete(
                    reverse("experiment-detail", args=[experiment.pk])
                ).status_code,
                409,
            )
            self.assertEqual(
                self.client.delete(
                    reverse("dataset-detail", args=[self.dataset.pk])
                ).status_code,
                409,
            )
        self.assertTrue(Path(self.dataset.file.path).is_file())

    def test_failed_configuration_can_be_edited_and_validation_checks_task_and_target(
        self,
    ):
        experiment = self.create_experiment()
        experiment.status = "failed"
        experiment.error_message = "Previous failure"
        experiment.save()
        url = reverse("experiment-detail", args=[experiment.pk])
        response = self.client.patch(
            url,
            {
                "task": "regression",
                "target_column": "price",
                "algorithms": ["linear_regression"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "ready")
        self.assertEqual(response.data["error_message"], "")
        for values in (
            {"target_column": "absent"},
            {"algorithms": ["unknown"]},
            {"algorithms": ["linear_regression", "linear_regression"]},
            {"task": "classification"},
        ):
            with self.subTest(values=values):
                self.assertEqual(
                    self.client.patch(url, values, format="json").status_code, 400
                )

    def test_timeout_marks_failed_and_worker_claims_a_job_only_once(self):
        experiment = self.create_experiment()
        self.start(experiment)
        claimed = claim_next_experiment()
        self.assertIsNone(claim_next_experiment())
        with patch(
            "experiments.worker.subprocess.run",
            side_effect=subprocess.TimeoutExpired("training", 300),
        ):
            execute_experiment(claimed)
        experiment.refresh_from_db()
        self.assertEqual(experiment.status, "failed")
        self.assertIn("time limit", experiment.error_message)

    def test_expired_claims_are_recovered_and_late_results_cannot_publish(self):
        experiment = self.create_experiment()
        self.start(experiment)
        claimed = claim_next_experiment()
        Experiment.objects.filter(pk=experiment.pk).update(
            started_at=timezone.now() - timedelta(seconds=400)
        )
        self.assertEqual(recover_stale_jobs(), 1)
        self.assertFalse(publish_results(claimed, [], self.media))
        self.start(experiment)
        claim_next_experiment()
        self.assertFalse(publish_results(claimed, [], self.media))

    def test_artifacts_are_cleaned_after_experiment_and_dataset_deletion(self):
        for delete_dataset in (False, True):
            experiment = self.create_experiment()
            self.complete(experiment)
            paths = [
                Path(result.model_file.path) for result in experiment.results.all()
            ]
            url = (
                reverse("dataset-detail", args=[self.dataset.pk])
                if delete_dataset
                else reverse("experiment-detail", args=[experiment.pk])
            )
            response = self.client.delete(url)
            self.assertEqual(response.status_code, 204)
            self.assertTrue(all(not path.exists() for path in paths))
            self.assertFalse(Experiment.objects.filter(pk=experiment.pk).exists())

    def test_publication_failure_rolls_back_rows_and_removes_written_files(self):
        experiment = self.create_experiment()
        self.start(experiment)
        claimed = claim_next_experiment()
        summaries = [
            {"algorithm": name, "metrics": {"accuracy": 1}, "is_best": index == 0}
            for index, name in enumerate(experiment.algorithms)
        ]
        (self.media / "logistic_regression.joblib").write_bytes(b"model")
        # The second artifact is missing: publishing must roll back the first one.
        with self.assertRaises(FileNotFoundError):
            publish_results(claimed, summaries, self.media)
        self.assertEqual(experiment.results.count(), 0)
        self.assertEqual(list((self.media / "artifacts").rglob("*.joblib")), [])

    def test_invalid_subprocess_response_is_a_failed_job(self):
        experiment = self.create_experiment()
        self.start(experiment)
        claimed = claim_next_experiment()
        with (
            self.assertLogs("experiments.worker", level="ERROR"),
            patch(
                "experiments.worker.subprocess.run",
                return_value=subprocess.CompletedProcess(
                    [], 0, stdout="not json", stderr=""
                ),
            ),
        ):
            execute_experiment(claimed)
        experiment.refresh_from_db()
        self.assertEqual(experiment.status, "failed")
        self.assertEqual(experiment.results.count(), 0)

    def test_running_jobs_without_claim_timestamp_can_be_recovered(self):
        experiment = self.create_experiment()
        experiment.status = "running"
        experiment.started_at = None
        experiment.save()
        self.assertEqual(recover_stale_jobs(), 1)
        experiment.refresh_from_db()
        self.assertEqual(experiment.status, "failed")
        self.assertEqual(self.start(experiment).status_code, 202)

    def test_partial_storage_write_is_removed_on_failure(self):
        from django.core.files.storage import FileSystemStorage

        experiment = self.create_experiment()
        self.start(experiment)
        claimed = claim_next_experiment()
        (self.media / "logistic_regression.joblib").write_bytes(b"model")

        def partial_write(storage, name, content):
            destination = Path(storage.path(name))
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(b"partial model")
            raise OSError("Disk full")

        with (
            patch.object(FileSystemStorage, "_save", partial_write),
            self.assertRaises(OSError),
        ):
            publish_results(
                claimed,
                [{"algorithm": "logistic_regression", "metrics": {}, "is_best": True}],
                self.media,
            )
        self.assertEqual(list((self.media / "artifacts").rglob("*.joblib")), [])
        self.assertEqual(experiment.results.count(), 0)

    def test_one_file_cleanup_failure_does_not_block_other_files_or_dataset_cleanup(
        self,
    ):
        from django.core.files.storage import FileSystemStorage

        experiment = self.create_experiment()
        experiment.status = "completed"
        experiment.save()
        paths = []
        for algorithm in experiment.algorithms:
            result = ExperimentResult(experiment=experiment, algorithm=algorithm)
            result.model_file.save(f"{algorithm}.joblib", ContentFile(b"model"))
            paths.append(Path(result.model_file.path))
        source = Path(self.dataset.file.path)
        original_delete = FileSystemStorage.delete
        failed_path = paths[0]

        def fail_one(storage, name):
            if Path(storage.path(name)) == failed_path:
                raise OSError("Cleanup failure")
            return original_delete(storage, name)

        with (
            patch.object(FileSystemStorage, "delete", fail_one),
            self.assertLogs("backend_config.storage", level="ERROR") as logs,
        ):
            response = self.client.delete(
                reverse("dataset-detail", args=[self.dataset.pk])
            )
        self.assertEqual(response.status_code, 204)
        self.assertTrue(failed_path.exists())
        self.assertFalse(paths[1].exists())
        self.assertFalse(source.exists())
        self.assertIn(failed_path.name, "\n".join(logs.output))

    def test_patch_validates_against_latest_task_even_if_an_old_instance_exists(self):
        from experiments.views import ExperimentDetailView

        experiment = self.create_experiment()
        Experiment.objects.filter(pk=experiment.pk).update(
            task="regression", algorithms=["linear_regression"]
        )
        with patch.object(ExperimentDetailView, "get_object", return_value=experiment):
            response = self.client.patch(
                reverse("experiment-detail", args=[experiment.pk]),
                {"algorithms": ["logistic_regression"]},
                format="json",
            )
        self.assertEqual(response.status_code, 400)
        experiment.refresh_from_db()
        self.assertEqual(experiment.algorithms, ["linear_regression"])

    def test_health_endpoint_is_public_and_read_only(self):
        self.client.credentials()
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(self.client.post(reverse("health")).status_code, 405)

    def test_algorithm_registry_is_exposed_by_authenticated_api(self):
        response = self.client.get(reverse("experiment-algorithms"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [item["id"] for item in response.data["classification"]],
            ["logistic_regression", "random_forest"],
        )
        self.assertIn(
            "linear_regression", [item["id"] for item in response.data["regression"]]
        )
