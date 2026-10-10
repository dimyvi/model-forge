import csv
import io

from django.urls import reverse
from rest_framework import serializers

from ml_engine.algorithms import validate_algorithms
from ml_engine.errors import AlgorithmValidationError

from .models import Experiment, ExperimentResult


class ExperimentResultSerializer(serializers.ModelSerializer):
    model_file = serializers.SerializerMethodField()

    def get_model_file(self, instance):
        if not instance.model_file:
            return None
        return reverse(
            "experiment-model-download", args=[instance.experiment_id, instance.pk]
        )

    class Meta:
        model = ExperimentResult
        fields = (
            "id",
            "algorithm",
            "metrics",
            "model_file",
            "is_best",
            "created_at",
        )
        read_only_fields = fields


class ExperimentSerializer(serializers.ModelSerializer):
    results = ExperimentResultSerializer(many=True, read_only=True)
    algorithms = serializers.ListField(child=serializers.CharField(), allow_empty=False)

    class Meta:
        model = Experiment
        fields = (
            "id",
            "dataset",
            "task",
            "target_column",
            "algorithms",
            "status",
            "queued_at",
            "started_at",
            "finished_at",
            "error_message",
            "created_at",
            "updated_at",
            "results",
        )
        read_only_fields = (
            "id",
            "status",
            "queued_at",
            "started_at",
            "finished_at",
            "error_message",
            "created_at",
            "updated_at",
            "results",
        )

    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()
        request = self.context.get("request")

        if request and request.method in ("PUT", "PATCH"):
            extra_kwargs["dataset"] = {"read_only": True}

        return extra_kwargs

    def validate_dataset(self, value):
        request = self.context.get("request")

        if request and value.owner_id != request.user.id:
            raise serializers.ValidationError(
                "Этот датасет принадлежит другому пользователю."
            )

        return value

    def validate_target_column(self, value):
        if not value.strip():
            raise serializers.ValidationError("Укажите целевую колонку.")

        return value

    def validate_algorithms(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("Выберите хотя бы один алгоритм.")

        return value

    def validate(self, attrs):
        instance = self.instance
        task = attrs.get(
            "task", instance.task if instance else Experiment.Task.CLASSIFICATION
        )
        algorithms = attrs.get("algorithms", instance.algorithms if instance else [])
        try:
            validate_algorithms(task, algorithms)
        except AlgorithmValidationError as error:
            raise serializers.ValidationError({"algorithms": str(error)}) from error

        dataset = attrs.get("dataset", instance.dataset if instance else None)
        target = attrs.get("target_column", instance.target_column if instance else "")
        if dataset is not None:
            try:
                with dataset.file.open("rb") as source:
                    header = next(
                        csv.reader(io.TextIOWrapper(source, encoding="utf-8-sig")), []
                    )
            except (OSError, UnicodeError, csv.Error) as error:
                raise serializers.ValidationError(
                    {"dataset": "Failed to read the CSV header."}
                ) from error
            if target not in header:
                raise serializers.ValidationError(
                    {
                        "target_column": "The target column is missing from the CSV header."
                    }
                )
        return attrs
