from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class HomePageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='map-viewer',
            password='test-password',
            is_staff=True,
        )

    def test_homepage_is_public(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'mapa-interativo')

    def test_admin_login_uses_antimary_branding(self):
        response = self.client.get('/admin/login/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/login.html')
        self.assertContains(response, 'ACESSO INTERNO')
        self.assertContains(response, '/static/mapa/css/login')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_admin_login_shows_error_for_invalid_credentials(self):
        response = self.client.post('/admin/login/', {
            'username': self.user.username,
            'password': 'wrong-password',
            'next': '/',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Não foi possível entrar')
        self.assertContains(response, 'login-page')

    def test_admin_login_authenticates_staff_and_redirects(self):
        response = self.client.post('/admin/login/', {
            'username': self.user.username,
            'password': 'test-password',
            'next': '/',
        })

        self.assertRedirects(response, '/')

    def test_health_endpoint_is_public_for_render(self):
        response = self.client.get('/health/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

    def test_homepage_displays_interactive_forest_map(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Floresta Estadual do Antimary')
        self.assertContains(response, 'mapa-interativo')
        self.assertContains(response, 'UGAI do Antimary')
        self.assertContains(response, 'Pontos coletados')
        self.assertContains(response, 'record-panel')
        self.assertContains(response, '/static/mapa/js/home')

    @patch('mapa.views.get_moradores')
    def test_moradores_api_returns_records_without_caching(self, get_moradores):
        get_moradores.return_value = [{
            'id': 'record-1',
            'latitude': -9.3,
            'longitude': -68.2,
            'fields': [],
            'images': [],
        }]
        response = self.client.get('/api/moradores/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['moradores'][0]['id'], 'record-1')
        self.assertEqual(response['Cache-Control'], 'no-store')
        get_moradores.assert_called_once_with()


class BootstrapAdminTests(TestCase):
    @patch.dict('os.environ', {}, clear=True)
    def test_bootstrap_skips_without_environment_credentials(self):
        call_command('bootstrap_admin')
        self.assertEqual(get_user_model().objects.count(), 0)

    @patch.dict(
        'os.environ',
        {
            'DJANGO_SUPERUSER_USERNAME': 'render-admin',
            'DJANGO_SUPERUSER_EMAIL': '',
            'DJANGO_SUPERUSER_PASSWORD': 'temporary-password',
        },
        clear=True,
    )
    def test_bootstrap_rejects_partial_environment_credentials(self):
        with self.assertRaises(CommandError):
            call_command('bootstrap_admin')
        self.assertEqual(get_user_model().objects.count(), 0)

    @patch.dict(
        'os.environ',
        {
            'DJANGO_SUPERUSER_USERNAME': 'render-admin',
            'DJANGO_SUPERUSER_EMAIL': 'admin@example.invalid',
            'DJANGO_SUPERUSER_PASSWORD': 'short',
        },
        clear=True,
    )
    def test_bootstrap_validates_password_before_creating_admin(self):
        with self.assertRaises(ValidationError):
            call_command('bootstrap_admin')
        self.assertFalse(get_user_model().objects.filter(username='render-admin').exists())

    @patch.dict(
        'os.environ',
        {
            'DJANGO_SUPERUSER_USERNAME': 'render-admin',
            'DJANGO_SUPERUSER_EMAIL': 'admin@example.invalid',
            'DJANGO_SUPERUSER_PASSWORD': 'Q7#fK9!wR2@pZ5$h',
        },
        clear=True,
    )
    def test_bootstrap_creates_staff_superuser(self):
        call_command('bootstrap_admin')

        user = get_user_model().objects.get(username='render-admin')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertTrue(user.check_password('Q7#fK9!wR2@pZ5$h'))
