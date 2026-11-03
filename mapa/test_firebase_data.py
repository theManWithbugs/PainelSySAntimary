from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from mapa.firebase_data import (
    FirebaseConfigurationError,
    _morador_record,
    _coordinates,
    _cloudinary_images,
    _get_firestore_client,
)


class FirebaseDataTests(SimpleTestCase):
    @patch.dict('os.environ', {'FIREBASE_SERVICE_ACCOUNT_JSON': '{}'}, clear=True)
    @patch('mapa.firebase_data.firestore.client')
    @patch('mapa.firebase_data.firebase_admin.initialize_app')
    @patch('mapa.firebase_data.credentials.Certificate')
    @patch('mapa.firebase_data.firebase_admin.get_app', side_effect=ValueError)
    def test_firestore_accepts_service_account_json_from_environment(
        self,
        get_app,
        certificate,
        initialize_app,
        firestore_client,
    ):
        initialize_app.return_value = object()

        _get_firestore_client()

        certificate.assert_called_once_with({})
        initialize_app.assert_called_once()
        firestore_client.assert_called_once()

    def test_coordinates_are_parsed_as_latitude_and_longitude(self):
        self.assertEqual(_coordinates('-9.3, -68.2'), (-9.3, -68.2))
        self.assertIsNone(_coordinates('not a coordinate'))
        self.assertIsNone(_coordinates('-91, -68'))

    def test_only_cloudinary_images_are_returned(self):
        images = _cloudinary_images([
            {
                'url': 'https://res.cloudinary.com/example/image/upload/photo.jpg',
                'nome': 'Foto de campo',
                'tipo': 'image',
            },
            {'url': 'https://other.example/photo.jpg', 'nome': 'Não confiável'},
            {'url': 'http://res.cloudinary.com/example/photo.jpg'},
            {'url': 'javascript:alert(1)'},
        ])

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0]['name'], 'Foto de campo')

    def test_morador_record_does_not_expose_internal_firestore_fields(self):
        document = SimpleNamespace(
            id='record-1',
            to_dict=lambda: {
                'nome': 'Pessoa de teste',
                'localizacao': '-9.3, -68.2',
                'foreign_key': 'internal reference',
                'simulado': False,
                'imagens': [],
            },
        )

        record = _morador_record(document)

        self.assertEqual(record['latitude'], -9.3)
        self.assertEqual(record['longitude'], -68.2)
        self.assertEqual(record['title'], 'Pessoa de teste')
        self.assertNotIn('foreign_key', record)
        self.assertNotIn('simulado', record)

    @patch.dict(
        'os.environ',
        {'LOCALAPPDATA': r'C:\Users\test\AppData\Local'},
        clear=True,
    )
    @patch('mapa.firebase_data.Path.is_file', return_value=False)
    def test_firestore_finds_credential_in_the_default_windows_location(self, is_file):
        with self.assertRaises(FirebaseConfigurationError):
            _get_firestore_client()
        is_file.assert_called_once_with()

    @patch.dict('os.environ', {'FIREBASE_SERVICE_ACCOUNT_JSON': '{invalid'}, clear=True)
    @patch('mapa.firebase_data.firebase_admin.get_app', side_effect=ValueError)
    def test_firestore_reports_invalid_json_environment_credential(self, get_app):
        with self.assertRaises(FirebaseConfigurationError):
            _get_firestore_client()
        get_app.assert_called_once_with()
