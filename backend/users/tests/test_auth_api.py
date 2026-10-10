from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase


class RegistrationApiTests(APITestCase):
    def setUp(self):
        self.url = reverse('register')
        self.payload = {
            'username': 'new-user',
            'email': 'new-user@example.com',
            'password': 'strong-pass-123',
        }

    def test_registration_creates_user_with_hashed_password(self):
        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='new-user')
        self.assertTrue(user.check_password('strong-pass-123'))
        self.assertNotEqual(user.password, 'strong-pass-123')
        self.assertNotIn('password', response.data)

    def test_registration_rejects_short_password(self):
        payload = {**self.payload, 'password': 'short'}

        response = self.client.post(self.url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data)
        self.assertFalse(User.objects.filter(username='new-user').exists())

    def test_registration_rejects_duplicate_username(self):
        User.objects.create_user(username='new-user', password='existing-pass')

        response = self.client.post(self.url, self.payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', response.data)


class LoginApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='dmitry',
            email='dmitry@example.com',
            password='strong-pass-123',
        )
        self.url = reverse('login')

    def test_login_returns_token_and_public_user_fields(self):
        response = self.client.post(
            self.url,
            {'username': 'dmitry', 'password': 'strong-pass-123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['token'], Token.objects.get(user=self.user).key)
        self.assertEqual(response.data['user']['id'], self.user.id)
        self.assertEqual(response.data['user']['username'], 'dmitry')
        self.assertEqual(response.data['user']['email'], 'dmitry@example.com')
        self.assertNotIn('password', response.data['user'])

    def test_login_rejects_incorrect_password(self):
        response = self.client.post(
            self.url,
            {'username': 'dmitry', 'password': 'incorrect-pass'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('detail', response.data)


class CurrentUserApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='dmitry',
            email='dmitry@example.com',
            password='strong-pass-123',
        )
        self.me_url = reverse('me')
        self.logout_url = reverse('logout')
        self.token = Token.objects.create(user=self.user)

    def authenticate(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

    def test_current_user_requires_authentication(self):
        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_current_user_returns_authenticated_user(self):
        self.authenticate()

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, {
            'id': self.user.id,
            'username': 'dmitry',
            'email': 'dmitry@example.com',
        })

    def test_logout_revokes_token(self):
        self.authenticate()

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(pk=self.token.pk).exists())
        self.assertEqual(
            self.client.get(self.me_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
