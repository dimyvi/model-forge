"""Make legacy active experiments without a run identifier editable again."""

from django.db import migrations
from django.utils import timezone


def recover_legacy_runs(apps, schema_editor):
    Experiment = apps.get_model("experiments", "Experiment")
    now = timezone.now()
    Experiment.objects.using(schema_editor.connection.alias).filter(
        status__in=["queued", "running"],
        run_id__isnull=True,
    ).update(
        status="failed",
        finished_at=now,
        updated_at=now,
        error_message="This experiment was created before worker integration. Review its settings and retry.",
    )


class Migration(migrations.Migration):
    dependencies = [("experiments", "0003_training_lifecycle")]
    operations = [migrations.RunPython(recover_legacy_runs, migrations.RunPython.noop)]
