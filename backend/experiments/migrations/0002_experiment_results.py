import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('experiments', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='experiment',
            name='status',
            field=models.CharField(
                choices=[
                    ('ready', 'Ready'),
                    ('queued', 'Queued'),
                    ('running', 'Running'),
                    ('completed', 'Completed'),
                    ('failed', 'Failed'),
                ],
                default='ready',
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name='experiment',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.CreateModel(
            name='ExperimentResult',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('algorithm', models.CharField(max_length=100)),
                ('metrics', models.JSONField(default=dict)),
                (
                    'model_file',
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to='models/',
                    ),
                ),
                ('is_best', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                (
                    'experiment',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='results',
                        to='experiments.experiment',
                    ),
                ),
            ],
            options={
                'ordering': ['-is_best', 'algorithm'],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('experiment', 'algorithm'),
                        name='unique_experiment_algorithm',
                    ),
                ],
            },
        ),
    ]
