"""Claim PostgreSQL jobs, run isolated training, and publish results atomically."""

import json
import logging
import os
import subprocess
import sys
import uuid
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.files import File
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone

from .models import Experiment, ExperimentResult

logger = logging.getLogger(__name__)


def recover_stale_jobs() -> int:
    """Fail expired claims; a run identifier prevents late result publication."""
    now = timezone.now()
    cutoff = now - timedelta(seconds=settings.ML_TRAINING_TIMEOUT + 60)
    return (
        Experiment.objects.filter(status=Experiment.Status.RUNNING)
        .filter(Q(started_at__lt=cutoff) | Q(started_at__isnull=True))
        .update(
            status=Experiment.Status.FAILED,
            finished_at=now,
            updated_at=now,
            error_message="The training worker stopped or exceeded its time limit. You can retry.",
        )
    )


def claim_next_experiment():
    """Lock a single queued row, allowing PostgreSQL workers to skip busy rows."""
    with transaction.atomic():
        queued = Experiment.objects.filter(status=Experiment.Status.QUEUED).order_by(
            "queued_at", "pk"
        )
        if connection.features.has_select_for_update_skip_locked:
            queued = queued.select_for_update(skip_locked=True)
        else:
            queued = queued.select_for_update()
        experiment = queued.first()
        if experiment is None:
            return None
        experiment.status = Experiment.Status.RUNNING
        if experiment.run_id is None:
            experiment.run_id = uuid.uuid4()
        experiment.started_at = timezone.now()
        experiment.save(update_fields=["status", "run_id", "started_at", "updated_at"])
    return experiment


def mark_failed(experiment, message):
    now = timezone.now()
    Experiment.objects.filter(
        pk=experiment.pk, run_id=experiment.run_id, status=Experiment.Status.RUNNING
    ).update(
        status=Experiment.Status.FAILED,
        error_message=message[:2000],
        finished_at=now,
        updated_at=now,
    )


def publish_results(experiment, summaries, directory):
    """Commit all models and metrics together; clean files if publication fails."""
    saved_files = []
    try:
        with transaction.atomic():
            current = (
                Experiment.objects.select_for_update().filter(pk=experiment.pk).first()
            )
            if (
                current is None
                or current.run_id != experiment.run_id
                or current.status != Experiment.Status.RUNNING
            ):
                return False
            records = []
            for summary in summaries:
                result = ExperimentResult(
                    experiment=current,
                    algorithm=summary["algorithm"],
                    metrics=summary["metrics"],
                    is_best=summary["is_best"],
                )
                filename = f"{summary['algorithm']}.joblib"
                name = f"user_{current.owner_id}/experiment_{current.pk}/{current.run_id}/{filename}"
                storage = result.model_file.storage
                expected_name = result.model_file.field.generate_filename(result, name)
                # Track the destination before storage can leave a partial write.
                saved_files.append((storage, expected_name))
                with (Path(directory) / filename).open("rb") as source:
                    result.model_file.save(name, File(source), save=False)
                if result.model_file.name != expected_name:
                    saved_files.append((storage, result.model_file.name))
                records.append(result)
            current.results.all().delete()
            ExperimentResult.objects.bulk_create(records)
            current.status = Experiment.Status.COMPLETED
            current.finished_at = timezone.now()
            current.error_message = ""
            current.save(
                update_fields=["status", "finished_at", "error_message", "updated_at"]
            )
        return True
    except BaseException:
        for storage, name in saved_files:
            try:
                storage.delete(name)
            except Exception:
                logger.exception(
                    "Could not remove failed artifact %s; retry file cleanup.", name
                )
        raise


def execute_experiment(experiment):
    """Run one claimed job outside the API process, enforcing its deadline."""
    try:
        with TemporaryDirectory(prefix="model-forge-training-") as directory:
            config = {
                "dataset_path": experiment.dataset.file.path,
                "target_column": experiment.target_column,
                "task": experiment.task,
                "algorithms": experiment.algorithms,
                "output_directory": directory,
                "metadata": {
                    "experiment_id": experiment.pk,
                    "dataset_id": experiment.dataset_id,
                    "run_id": str(experiment.run_id),
                },
            }
            environment = {
                **os.environ,
                "OMP_NUM_THREADS": "1",
                "OPENBLAS_NUM_THREADS": "1",
                "MKL_NUM_THREADS": "1",
            }
            process = subprocess.run(
                [sys.executable, "-m", "ml_engine.runner"],
                input=json.dumps(config),
                capture_output=True,
                text=True,
                cwd=settings.BASE_DIR,
                env=environment,
                timeout=settings.ML_TRAINING_TIMEOUT,
                check=False,
            )
            if process.stderr:
                logger.warning(
                    "Training output for experiment %s: %s",
                    experiment.pk,
                    process.stderr[-4000:],
                )
            try:
                payload = json.loads(process.stdout)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    "The training subprocess returned an invalid response."
                ) from error
            if process.returncode != 0:
                mark_failed(
                    experiment,
                    payload.get("error", "Training failed. Check the worker logs."),
                )
                return
            summaries = payload["results"]
            if (
                not summaries
                or [item["algorithm"] for item in summaries] != experiment.algorithms
                or sum(item["is_best"] for item in summaries) != 1
            ):
                raise RuntimeError(
                    "The training subprocess returned incomplete results."
                )
            publish_results(experiment, summaries, directory)
    except subprocess.TimeoutExpired:
        mark_failed(
            experiment,
            f"Training exceeded the time limit of {settings.ML_TRAINING_TIMEOUT} seconds. Try a smaller dataset.",
        )
    except (KeyboardInterrupt, SystemExit):
        mark_failed(experiment, "Training was interrupted. You can retry.")
        raise
    except Exception:
        logger.exception("Training failed for experiment %s", experiment.pk)
        mark_failed(experiment, "Training failed unexpectedly. Check the worker logs.")
