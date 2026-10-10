"""Process training jobs outside the Django HTTP server."""

import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections, connection

from experiments.worker import (
    claim_next_experiment,
    execute_experiment,
    recover_stale_jobs,
)


class Command(BaseCommand):
    help = "Process queued experiments using an isolated training subprocess."

    def add_arguments(self, parser):
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process at most one queued job, then exit.",
        )
        parser.add_argument(
            "--poll-interval", type=float, default=settings.ML_WORKER_POLL_INTERVAL
        )

    def handle(self, *args, **options):
        if options["poll_interval"] <= 0 or settings.ML_TRAINING_TIMEOUT <= 0:
            raise CommandError(
                "The poll interval and training timeout must be positive."
            )
        self.stdout.write("ML worker started. Waiting for queued experiments.")
        try:
            while True:
                if not connection.in_atomic_block:
                    close_old_connections()
                recovered = recover_stale_jobs()
                if recovered:
                    self.stdout.write(
                        f"Marked {recovered} stale experiment(s) as failed."
                    )
                experiment = claim_next_experiment()
                if experiment is not None:
                    self.stdout.write(f"Training experiment #{experiment.pk}.")
                    execute_experiment(experiment)
                    self.stdout.write(
                        f"Finished processing experiment #{experiment.pk}."
                    )
                if options["once"]:
                    return
                if experiment is None:
                    time.sleep(options["poll_interval"])
        except KeyboardInterrupt:
            self.stdout.write("ML worker stopped.")
