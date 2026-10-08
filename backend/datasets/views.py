from pathlib import Path

from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from .models import Dataset
from .serializers import DatasetDetailSerializer, DatasetSerializer


class DatasetListCreateView(generics.ListCreateAPIView):
    serializer_class = DatasetSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dataset.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        uploaded_file = serializer.validated_data['file']
        original_name = Path(uploaded_file.name).name
        stem = Path(original_name).stem
        suffix = Path(original_name).suffix
        existing_names = {
            Path(name).name
            for name in Dataset.objects.filter(
                owner=self.request.user,
            ).values_list('file', flat=True)
        }

        candidate_name = original_name
        number = 1
        while candidate_name in existing_names:
            candidate_name = f'{stem} ({number}){suffix}'
            number += 1

        uploaded_file.name = candidate_name
        serializer.save(owner=self.request.user, file=uploaded_file)


class DatasetDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = DatasetDetailSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Dataset.objects.filter(owner=self.request.user)

    def perform_destroy(self, instance):
        instance.file.delete(save=False)
        instance.delete()
