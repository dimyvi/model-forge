from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from datasets.models import Dataset
from experiments.models import Experiment, ExperimentResult


class ExperimentApiTests(APITestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.user = User.objects.create_user(
            username="owner", password="strong-pass-123"
        )
        self.other_user = User.objects.create_user(
            username="another-owner", password="strong-pass-123"
        )
        self.dataset = Dataset.objects.create(
            owner=self.user,
            file=SimpleUploadedFile(
                "train.csv", b"value,price,label\n1,10,a\n2,20,b\n"
            ),
        )
        self.other_dataset = Dataset.objects.create(
            owner=self.other_user,
            file=SimpleUploadedFile("private.csv", b"value,label\n1,a\n2,b\n"),
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        self.list_url = reverse("experiment-list-create")

    def create_experiment(self, owner=None, dataset=None, **values):
        return Experiment.objects.create(
            owner=owner or self.user,
            dataset=dataset or self.dataset,
            target_column=values.pop("target_column", "label"),
            algorithms=values.pop("algorithms", ["logistic_regression"]),
            **values,
        )

    def test_create_experiment_assigns_current_user_and_default_status(self):
        response = self.client.post(
            self.list_url,
            {
                "dataset": self.dataset.id,
                "task": Experiment.Task.CLASSIFICATION,
                "target_column": "label",
                "algorithms": ["logistic_regression"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        experiment = Experiment.objects.get(pk=response.data["id"])
        self.assertEqual(experiment.owner, self.user)
        self.assertEqual(experiment.dataset, self.dataset)
        self.assertEqual(experiment.status, Experiment.Status.READY)

    def test_create_rejects_dataset_owned_by_another_user(self):
        response = self.client.post(
            self.list_url,
            {
                "dataset": self.other_dataset.id,
                "task": Experiment.Task.CLASSIFICATION,
                "target_column": "label",
                "algorithms": ["logistic_regression"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("dataset", response.data)
        self.assertEqual(Experiment.objects.count(), 0)

    def test_create_rejects_blank_target_column(self):
        response = self.client.post(
            self.list_url,
            {
                "dataset": self.dataset.id,
                "target_column": "   ",
                "algorithms": ["logistic_regression"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("target_column", response.data)

    def test_create_rejects_empty_algorithm_list(self):
        response = self.client.post(
            self.list_url,
            {
                "dataset": self.dataset.id,
                "target_column": "label",
                "algorithms": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("algorithms", response.data)

    def test_list_and_detail_only_expose_owned_experiments(self):
        own_experiment = self.create_experiment()
        foreign_experiment = self.create_experiment(
            owner=self.other_user,
            dataset=self.other_dataset,
        )

        list_response = self.client.get(self.list_url)
        detail_response = self.client.get(
            reverse("experiment-detail", args=[foreign_experiment.id])
        )

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in list_response.data],
            [own_experiment.id],
        )
        self.assertEqual(
            detail_response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_ready_experiment_can_be_updated_but_dataset_stays_unchanged(self):
        experiment = self.create_experiment()

        response = self.client.patch(
            reverse("experiment-detail", args=[experiment.id]),
            {
                "dataset": self.other_dataset.id,
                "task": Experiment.Task.REGRESSION,
                "target_column": "price",
                "algorithms": ["linear_regression"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        experiment.refresh_from_db()
        self.assertEqual(experiment.dataset, self.dataset)
        self.assertEqual(experiment.task, Experiment.Task.REGRESSION)
        self.assertEqual(experiment.target_column, "price")

    def test_non_ready_experiment_cannot_be_updated(self):
        experiment = self.create_experiment(status=Experiment.Status.RUNNING)

        response = self.client.patch(
            reverse("experiment-detail", args=[experiment.id]),
            {"target_column": "new-label"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        experiment.refresh_from_db()
        self.assertEqual(experiment.target_column, "label")

    def test_detail_includes_saved_results_and_metrics(self):
        experiment = self.create_experiment()
        ExperimentResult.objects.create(
            experiment=experiment,
            algorithm="logistic_regression",
            metrics={"accuracy": 0.92},
            is_best=True,
        )

        response = self.client.get(reverse("experiment-detail", args=[experiment.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["metrics"],
            {"accuracy": 0.92},
        )
        self.assertTrue(response.data["results"][0]["is_best"])

    def test_owner_can_delete_experiment(self):
        experiment = self.create_experiment()

        response = self.client.delete(
            reverse("experiment-detail", args=[experiment.id])
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Experiment.objects.filter(pk=experiment.id).exists())

    def test_experiment_api_requires_authentication(self):
        self.client.credentials()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
