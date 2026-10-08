from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from .models import Experiment
from .serializers import ExperimentSerializer


class ExperimentListCreateView(generics.ListCreateAPIView):
    serializer_class = ExperimentSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Experiment.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class ExperimentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExperimentSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Experiment.objects.filter(owner=self.request.user)

    def perform_update(self, serializer):
        if serializer.instance.status != Experiment.Status.READY:
            raise ValidationError(
                'Можно редактировать только эксперимент со статусом ready.'
            )

        serializer.save()
