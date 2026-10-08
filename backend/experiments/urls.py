from django.urls import path

from .views import ExperimentDetailView, ExperimentListCreateView


urlpatterns = [
    path('', ExperimentListCreateView.as_view(), name='experiment-list-create'),
    path('<int:pk>/', ExperimentDetailView.as_view(), name='experiment-detail'),
]
