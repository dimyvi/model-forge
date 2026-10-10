from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from datasets.models import Dataset


def csv_file(name='train.csv', content='id,label\n1,yes\n'):
    return SimpleUploadedFile(
        name,
        content.encode('utf-8'),
        content_type='text/csv',
    )


class DatasetApiTests(APITestCase):
    def setUp(self):
        self.media_directory = TemporaryDirectory()
        self.addCleanup(self.media_directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=self.media_directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)

        self.user = User.objects.create_user(
            username='owner', password='strong-pass-123'
        )
        self.other_user = User.objects.create_user(
            username='another-owner', password='strong-pass-123'
        )
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        self.list_url = reverse('dataset-list-create')

    def create_dataset(self, owner, name='train.csv', content='id,label\n1,yes\n'):
        return Dataset.objects.create(
            owner=owner,
            file=csv_file(name, content),
        )

    def test_list_only_returns_datasets_owned_by_current_user(self):
        own_dataset = self.create_dataset(self.user)
        self.create_dataset(self.other_user, name='private.csv')

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], own_dataset.id)

    def test_upload_csv_and_assign_owner_from_authentication(self):
        response = self.client.post(
            self.list_url,
            {'file': csv_file()},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        dataset = Dataset.objects.get(pk=response.data['id'])
        self.assertEqual(dataset.owner, self.user)
        self.assertEqual(dataset.file.name, 'datasets/train.csv')

    def test_same_filename_gets_a_unique_numbered_name(self):
        first = self.client.post(
            self.list_url, {'file': csv_file()}, format='multipart'
        )
        second = self.client.post(
            self.list_url, {'file': csv_file()}, format='multipart'
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            Dataset.objects.get(pk=first.data['id']).file.name,
            'datasets/train.csv',
        )
        self.assertEqual(
            Dataset.objects.get(pk=second.data['id']).file.name,
            'datasets/train_1.csv',
        )

    def test_upload_rejects_non_csv_file(self):
        response = self.client.post(
            self.list_url,
            {'file': csv_file(name='train.json', content='{}')},
            format='multipart',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('file', response.data)
        self.assertEqual(Dataset.objects.count(), 0)

    def test_detail_returns_csv_columns_row_count_and_first_ten_rows(self):
        rows = ''.join(f'{index},class-{index}\n' for index in range(12))
        dataset = self.create_dataset(
            self.user,
            content=f'id,label\n{rows}',
        )

        response = self.client.get(
            reverse('dataset-detail', args=[dataset.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['columns'], ['id', 'label'])
        self.assertEqual(response.data['rows_count'], 12)
        self.assertEqual(len(response.data['preview']), 10)
        self.assertEqual(response.data['preview'][0], {
            'id': '0',
            'label': 'class-0',
        })

    def test_owner_can_delete_dataset_and_uploaded_file(self):
        dataset = self.create_dataset(self.user)
        saved_path = Path(dataset.file.path)
        self.assertTrue(saved_path.is_file())

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(
                reverse('dataset-detail', args=[dataset.id])
            )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Dataset.objects.filter(pk=dataset.id).exists())
        self.assertFalse(saved_path.exists())

    def test_user_cannot_read_or_delete_another_users_dataset(self):
        dataset = self.create_dataset(self.other_user, name='private.csv')
        detail_url = reverse('dataset-detail', args=[dataset.id])

        read_response = self.client.get(detail_url)
        delete_response = self.client.delete(detail_url)

        self.assertEqual(read_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delete_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Dataset.objects.filter(pk=dataset.id).exists())

    def test_dataset_api_requires_authentication(self):
        self.client.credentials()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
