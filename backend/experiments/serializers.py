from rest_framework import serializers

from .models import Experiment, ExperimentResult


class ExperimentResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExperimentResult
        fields = (
            'id',
            'algorithm',
            'metrics',
            'model_file',
            'is_best',
            'created_at',
        )
        read_only_fields = fields


class ExperimentSerializer(serializers.ModelSerializer):
    results = ExperimentResultSerializer(many=True, read_only=True)

    class Meta:
        model = Experiment
        fields = (
            'id',
            'dataset',
            'task',
            'target_column',
            'algorithms',
            'status',
            'created_at',
            'updated_at',
            'results',
        )
        read_only_fields = (
            'id',
            'status',
            'created_at',
            'updated_at',
            'results',
        )

    def get_extra_kwargs(self):
        extra_kwargs = super().get_extra_kwargs()
        request = self.context.get('request')

        if request and request.method in ('PUT', 'PATCH'):
            extra_kwargs['dataset'] = {'read_only': True}

        return extra_kwargs

    def validate_dataset(self, value):
        request = self.context.get('request')

        if request and value.owner_id != request.user.id:
            raise serializers.ValidationError(
                'Этот датасет принадлежит другому пользователю.'
            )

        return value

    def validate_target_column(self, value):
        if not value.strip():
            raise serializers.ValidationError(
                'Укажите целевую колонку.'
            )

        return value

    def validate_algorithms(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError(
                'Выберите хотя бы один алгоритм.'
            )

        return value
