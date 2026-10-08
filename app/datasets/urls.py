from django.urls import path

from .views import DatasetDetailView, DatasetListCreateView


urlpatterns = [
    path('', DatasetListCreateView.as_view(), name='dataset-list-create'),
    path('<int:pk>/', DatasetDetailView.as_view(), name='dataset-detail'),
]
