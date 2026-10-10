"""Verify queue locks against real independent database connections."""

import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event

from django.contrib.auth.models import User
from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from datasets.models import Dataset
from experiments.models import Experiment
from experiments.services import ExperimentConflict, enqueue_experiment
from experiments.worker import claim_next_experiment


@skipUnlessDBFeature("has_select_for_update_skip_locked")
class QueueConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create(username="queue-owner")
        self.dataset = Dataset.objects.create(
            owner=self.user, file="datasets/queue.csv"
        )

    def experiment(self, **overrides):
        return Experiment.objects.create(
            owner=self.user,
            dataset=self.dataset,
            target_column="label",
            algorithms=["logistic_regression"],
            **overrides,
        )

    def test_worker_skips_another_workers_locked_row(self):
        first = self.experiment(
            status="queued", queued_at=timezone.now(), run_id=uuid.uuid4()
        )
        second = self.experiment(
            status="queued", queued_at=timezone.now(), run_id=uuid.uuid4()
        )
        locked, release = Event(), Event()

        def hold_first():
            close_old_connections()
            try:
                with transaction.atomic():
                    Experiment.objects.select_for_update().get(pk=first.pk)
                    locked.set()
                    if not release.wait(10):
                        raise TimeoutError("The test did not release the queue row.")
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=1) as pool:
            holding = pool.submit(hold_first)
            try:
                self.assertTrue(locked.wait(5))
                self.assertEqual(claim_next_experiment().pk, second.pk)
            finally:
                release.set()
            holding.result(timeout=5)
        self.assertEqual(claim_next_experiment().pk, first.pk)
        self.assertIsNone(claim_next_experiment())

    def test_simultaneous_start_requests_enqueue_only_one_run(self):
        experiment = self.experiment()
        begin = Event()

        def start():
            close_old_connections()
            try:
                begin.wait(5)
                try:
                    return enqueue_experiment(experiment.pk, self.user).run_id
                except ExperimentConflict:
                    return "conflict"
            finally:
                connection.close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            requests = [pool.submit(start), pool.submit(start)]
            begin.set()
            outcomes = [future.result(timeout=10) for future in requests]
        self.assertEqual(outcomes.count("conflict"), 1)
        experiment.refresh_from_db()
        self.assertEqual(experiment.status, "queued")
        self.assertIn(experiment.run_id, outcomes)
