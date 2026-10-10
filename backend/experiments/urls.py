from django.urls import path

from .views import (
    AlgorithmListView,
    ExperimentDetailView,
    ExperimentListCreateView,
    ExperimentStartView,
    ModelDownloadView,
)

urlpatterns = [
    path("", ExperimentListCreateView.as_view(), name="experiment-list-create"),
    path("algorithms/", AlgorithmListView.as_view(), name="experiment-algorithms"),
    path("<int:pk>/", ExperimentDetailView.as_view(), name="experiment-detail"),
    path("<int:pk>/start/", ExperimentStartView.as_view(), name="experiment-start"),
    path(
        "<int:pk>/results/<int:result_id>/download/",
        ModelDownloadView.as_view(),
        name="experiment-model-download",
    ),
]
