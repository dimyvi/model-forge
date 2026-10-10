from pathlib import Path

from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ml_engine.algorithms import ALGORITHM_REGISTRY, available_algorithms

from .models import Experiment, ExperimentResult
from .serializers import ExperimentSerializer
from .services import (
    ACTIVE_STATUSES,
    EDITABLE_STATUSES,
    ExperimentConflict,
    enqueue_experiment,
)


class ExperimentListCreateView(generics.ListCreateAPIView):
    serializer_class = ExperimentSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Experiment.objects.filter(owner=self.request.user).prefetch_related(
            "results"
        )

    def perform_create(self, serializer):
        # Serialize creation with dataset deletion so a validated dataset cannot disappear.
        with transaction.atomic():
            dataset = serializer.validated_data["dataset"]
            get_object_or_404(
                type(dataset).objects.select_for_update(),
                pk=dataset.pk,
                owner=self.request.user,
            )
            serializer.save(owner=self.request.user)


class ExperimentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExperimentSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Experiment.objects.filter(owner=self.request.user).prefetch_related(
            "results"
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        with transaction.atomic():
            instance = get_object_or_404(
                Experiment.objects.select_for_update(),
                pk=kwargs["pk"],
                owner=self.request.user,
            )
            if instance.status not in EDITABLE_STATUSES:
                raise ValidationError("Only ready or failed experiments can be edited.")
            # Validate the merged configuration while holding the same lock as start.
            serializer = self.get_serializer(
                instance, data=request.data, partial=partial
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(
                status=Experiment.Status.READY,
                error_message="",
                run_id=None,
                queued_at=None,
                started_at=None,
                finished_at=None,
            )
        return Response(serializer.data)

    def perform_destroy(self, instance):
        with transaction.atomic():
            instance = get_object_or_404(
                Experiment.objects.select_for_update(),
                pk=instance.pk,
                owner=self.request.user,
            )
            if instance.status in ACTIVE_STATUSES:
                raise ExperimentConflict(
                    "Wait for training to finish before deleting the experiment."
                )
            instance.delete()


class ExperimentStartView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        experiment = enqueue_experiment(pk, request.user)
        return Response(
            ExperimentSerializer(experiment, context={"request": request}).data,
            status=202,
        )


class AlgorithmListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
                task: [
                    {"id": name, "name": label}
                    for name, label in available_algorithms(task).items()
                ]
                for task in ALGORITHM_REGISTRY
            }
        )


class ModelDownloadView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, result_id):
        result = get_object_or_404(
            ExperimentResult.objects.select_related("experiment"),
            pk=result_id,
            experiment_id=pk,
            experiment__owner=request.user,
            experiment__status=Experiment.Status.COMPLETED,
        )
        if not result.model_file:
            raise Http404("The model file is not available.")
        try:
            source = result.model_file.open("rb")
        except OSError as error:
            raise Http404("The model file is not available.") from error
        response = FileResponse(
            source,
            as_attachment=True,
            filename=Path(result.model_file.name).name,
            content_type="application/octet-stream",
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
