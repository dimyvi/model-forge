"""Remove artifacts after successful result deletion, including cascade deletion."""

from django.db.models.signals import post_delete
from django.dispatch import receiver

from backend_config.storage import delete_file_after_commit

from .models import ExperimentResult


@receiver(post_delete, sender=ExperimentResult)
def delete_model_file(sender, instance, **kwargs):
    if instance.model_file:
        storage, name = instance.model_file.storage, instance.model_file.name
        delete_file_after_commit(storage, name)
