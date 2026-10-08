from django.contrib.auth.models import User
from django.db import models

from datasets.models import Dataset


class Experiment(models.Model):
    class Task(models.TextChoices):
        CLASSIFICATION = 'classification', 'Classification'
        REGRESSION = 'regression', 'Regression'

    class Status(models.TextChoices):
        READY = 'ready', 'Ready'
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'

    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='experiments',
    )
    dataset = models.ForeignKey(
        Dataset,
        on_delete=models.CASCADE,
        related_name='experiments',
    )
    task = models.CharField(
        max_length=32,
        choices=Task.choices,
        default=Task.CLASSIFICATION,
    )
    target_column = models.CharField(max_length=255)
    algorithms = models.JSONField(default=list)
    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.READY,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Experiment #{self.pk}'


class ExperimentResult(models.Model):
    experiment = models.ForeignKey(
        Experiment,
        on_delete=models.CASCADE,
        related_name='results',
    )
    algorithm = models.CharField(max_length=100)
    metrics = models.JSONField(default=dict)
    model_file = models.FileField(
        upload_to='models/',
        blank=True,
        null=True,
    )
    is_best = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_best', 'algorithm']
        constraints = [
            models.UniqueConstraint(
                fields=['experiment', 'algorithm'],
                name='unique_experiment_algorithm',
            ),
        ]

    def __str__(self):
        return f'{self.experiment} — {self.algorithm}'
