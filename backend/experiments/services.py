"""Transactional experiment lifecycle rules shared by API and worker."""

import uuid

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import APIException

from datasets.models import Dataset

from .models import Experiment

ACTIVE_STATUSES = (Experiment.Status.QUEUED, Experiment.Status.RUNNING)
EDITABLE_STATUSES = (Experiment.Status.READY, Experiment.Status.FAILED)


class ExperimentConflict(APIException):
    status_code = 409
    default_detail = "The experiment cannot be changed in its current state."
    default_code = "experiment_conflict"


def enqueue_experiment(experiment_id, user):
    """Enqueue a configuration once, using the same lock order as dataset deletion."""
    with transaction.atomic():
        existing = get_object_or_404(Experiment, pk=experiment_id, owner=user)
        get_object_or_404(
            Dataset.objects.select_for_update(), pk=existing.dataset_id, owner=user
        )
        experiment = get_object_or_404(
            Experiment.objects.select_for_update(), pk=experiment_id, owner=user
        )
        if experiment.status not in EDITABLE_STATUSES:
            raise ExperimentConflict("Only ready or failed experiments can be started.")
        experiment.results.all().delete()
        experiment.run_id = uuid.uuid4()
        experiment.status = Experiment.Status.QUEUED
        experiment.queued_at = timezone.now()
        experiment.started_at = None
        experiment.finished_at = None
        experiment.error_message = ""
        experiment.save()
    return experiment
