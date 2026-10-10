import csv
import io

from rest_framework import serializers

from .models import Dataset


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dataset
        fields = ('id', 'file', 'uploaded_at')
        read_only_fields = ('id', 'uploaded_at')

    def validate_file(self, value):
        if value.size > 10 * 1024 * 1024:
            raise serializers.ValidationError('The CSV must not exceed 10 MiB.')
        if not value.name.lower().endswith('.csv'):
            raise serializers.ValidationError(
                'Пока поддерживаются только CSV-файлы.'
            )

        return value


class DatasetDetailSerializer(DatasetSerializer):
    columns = serializers.SerializerMethodField()
    rows_count = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()

    class Meta(DatasetSerializer.Meta):
        fields = DatasetSerializer.Meta.fields + (
            'columns',
            'rows_count',
            'preview',
        )

    def _read_csv(self, instance):
        columns = []
        preview = []
        rows_count = 0

        with instance.file.open('rb') as uploaded_file:
            text_file = io.TextIOWrapper(
                uploaded_file,
                encoding='utf-8-sig',
                newline='',
            )
            reader = csv.DictReader(text_file)
            columns = reader.fieldnames or []

            for row in reader:
                rows_count += 1
                if len(preview) < 10:
                    preview.append(dict(row))

        return columns, rows_count, preview

    def _get_csv_data(self, instance):
        try:
            return self._read_csv(instance)
        except (UnicodeDecodeError, csv.Error) as error:
            raise serializers.ValidationError(
                {'file': f'Не удалось прочитать CSV: {error}'}
            ) from error

    def get_columns(self, instance):
        columns, _, _ = self._get_csv_data(instance)
        return columns

    def get_rows_count(self, instance):
        _, rows_count, _ = self._get_csv_data(instance)
        return rows_count

    def get_preview(self, instance):
        _, _, preview = self._get_csv_data(instance)
        return preview
