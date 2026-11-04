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

    def test_homepage_requires_pin(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mapa/pin.html')
        self.assertContains(response, 'PIN de 4 dígitos')
        self.assertContains(response, '/static/mapa/images/amanhecer-floresta-amazonica.')
        self.assertNotContains(response, 'mapa-interativo')

    def test_homepage_rejects_invalid_pin(self):
        response = self.client.post('/', {'pin': '0000'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'PIN inválido')
        self.assertTemplateUsed(response, 'mapa/pin.html')

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
        response = self.client.post('/', {'pin': '1242'})
        self.assertRedirects(response, '/')

        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Floresta Estadual do Antimary')
        self.assertContains(response, 'mapa-interativo')
        self.assertContains(response, 'UGAI do Antimary')
        self.assertContains(response, 'Pontos coletados')
        self.assertContains(response, 'record-panel')
        self.assertContains(response, '/static/mapa/js/home')

    def test_indicators_page_requires_pin(self):
        response = self.client.get('/indicadores/')

        self.assertRedirects(response, '/')

    def test_indicators_page_displays_dashboard(self):
        self.client.post('/', {'pin': '1242'})

        response = self.client.get('/indicadores/')

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'mapa/indicadores.html')
        self.assertContains(response, 'Todos os cadastrados')
        self.assertContains(response, 'Gerar relatório PDF')
        self.assertContains(response, '/static/mapa/js/indicadores')
        self.assertEqual(response['Cache-Control'], 'no-store')

    @patch('mapa.views.get_moradores')
    def test_moradores_api_returns_records_without_caching(self, get_moradores):
        self.client.post('/', {'pin': '1242'})
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

    @patch('mapa.views.get_moradores')
    def test_moradores_api_requires_pin(self, get_moradores):
        response = self.client.get('/api/moradores/')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error'], 'Informe o PIN para acessar os dados do mapa.')
        self.assertEqual(response['Cache-Control'], 'no-store')
        get_moradores.assert_not_called()

    @patch('mapa.views.get_cadastros_summary')
    def test_indicators_api_returns_summary_without_caching(self, get_summary):
        self.client.post('/', {'pin': '1242'})
        summary = {
            'records': [{
                'id': 'record-1',
                'name': 'Cadastro um',
                'colony': 'Colônia Esperança',
                'registered_at': '2025-03-14',
                'linked_residents': 2,
            }],
            'total_records': 1,
            'linked_residents': 2,
            'by_colony': [{'label': 'Colônia Esperança', 'count': 1}],
            'residents_by_gender': [{'label': 'Feminino', 'count': 2}],
        }
        get_summary.return_value = summary

        response = self.client.get('/api/indicadores/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), summary)
        self.assertEqual(response['Cache-Control'], 'no-store')
        get_summary.assert_called_once_with()

    @patch('mapa.views.get_cadastros_summary')
    def test_indicators_api_requires_pin(self, get_summary):
        response = self.client.get('/api/indicadores/')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response['Cache-Control'], 'no-store')
        get_summary.assert_not_called()

    @patch('mapa.views.get_morador_detail')
    def test_morador_detail_api_returns_record_without_caching(self, get_detail):
        self.client.post('/', {'pin': '1242'})
        detail = {
            'id': 'record-1',
            'title': 'Cadastro um',
            'coordinates': None,
            'fields': [{'label': 'Colônia', 'value': 'Esperança'}],
            'residents': [],
            'images': [],
        }
        get_detail.return_value = detail

        response = self.client.get('/api/moradores/record-1/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), detail)
        self.assertEqual(response['Cache-Control'], 'no-store')
        get_detail.assert_called_once_with('record-1')

    @patch('mapa.views.get_morador_detail')
    def test_morador_detail_api_requires_pin(self, get_detail):
        response = self.client.get('/api/moradores/record-1/')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response['Cache-Control'], 'no-store')
        get_detail.assert_not_called()

    @patch('mapa.views.get_morador_detail', return_value=None)
    def test_morador_detail_api_returns_not_found_for_missing_record(self, get_detail):
        self.client.post('/', {'pin': '1242'})

        response = self.client.get('/api/moradores/missing/')

        self.assertEqual(response.status_code, 404)
        get_detail.assert_called_once_with('missing')


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
