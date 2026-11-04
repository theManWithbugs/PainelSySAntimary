import json
import os
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

import firebase_admin
from firebase_admin import credentials, firestore
from google.api_core.exceptions import GoogleAPICallError


class FirebaseConfigurationError(Exception):
    pass


class FirebaseUnavailable(Exception):
    pass


DISPLAY_FIELDS = (
    ('nome', 'Nome'),
    ('colonia', 'Colônia'),
    ('registrado_em', 'Data do registro'),
    ('ano_moradia', 'Ano de início na moradia'),
    ('ano_compra_ocupacao', 'Ano de compra ou ocupação'),
    ('denominacao_historica', 'Denominação histórica'),
    ('descricao_propriedade', 'Descrição da propriedade'),
    ('origem_ocupacao', 'Origem da ocupação'),
    ('origem_ocupacao_outro', 'Outra origem da ocupação'),
    ('morava_antes_criacao_uc', 'Morava na área antes da criação da unidade'),
    ('area_total_ha', 'Área total (ha)'),
    ('area_floresta_ha', 'Área de floresta (ha)'),
    ('area_pastagem_ha', 'Área de pastagem (ha)'),
    ('cria_gado', 'Cria gado'),
    ('cabecas_gado', 'Quantidade de cabeças de gado'),
    ('extrativismo', 'Atividades extrativistas'),
    ('extrativismo_outra', 'Outra atividade extrativista'),
    ('principal_sustento', 'Principal fonte de sustento'),
    ('principal_sustento_outra', 'Outra fonte de sustento'),
    ('destino_producao', 'Destino da produção'),
    ('quantidade_pessoas', 'Pessoas na residência'),
    ('forca_trabalho', 'Força de trabalho'),
    ('beneficios', 'Benefícios'),
    ('beneficios_outro', 'Outro benefício'),
    ('grupos_tradicionais', 'Grupos tradicionais'),
    ('grupos_tradicionais_outro', 'Outro grupo tradicional'),
    ('observado_propriedade', 'Observações sobre a propriedade'),
    ('observado_propriedade_outro', 'Outra observação sobre a propriedade'),
    ('recursos_vitais', 'Recursos naturais importantes'),
    ('recursos_vitais_outro', 'Outro recurso natural'),
    ('governanca', 'Participação e governança'),
    ('resolucao_conflitos', 'Resolução de conflitos'),
    ('resolucao_conflitos_outro', 'Outra forma de resolução de conflitos'),
    ('sistema_roca', 'Sistema de roça'),
    ('roca_corte_queima_pousio', 'Corte, queima e pousio'),
    ('plantas_medicinais', 'Plantas medicinais'),
    ('caca_subsistencia', 'Caça de subsistência'),
    ('pesca_subsistencia', 'Pesca de subsistência'),
    ('sabe_que_mora_uc', 'Conhece a unidade de conservação'),
    ('situacao_visita', 'Situação da visita'),
    ('observacoes_entrevistador', 'Observações do entrevistador'),
    ('entrevistador', 'Entrevistador'),
)

RESIDENT_FIELDS = (
    ('dataNascimento', 'Data de nascimento'),
    ('escolaridade', 'Escolaridade'),
    ('estadoCivil', 'Estado civil'),
    ('genero', 'Gênero'),
    ('relacao', 'Relação familiar'),
)


def _get_firestore_client():
    credential_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')
    credential_path = os.environ.get('FIREBASE_SERVICE_ACCOUNT_PATH')
    if not credential_json and not credential_path:
        local_app_data = os.environ.get('LOCALAPPDATA')
        if local_app_data:
            credential_path = str(
                Path(local_app_data) / 'Antimary' / 'firebase-service-account.json'
            )
    if not credential_json and not credential_path:
        raise FirebaseConfigurationError(
            'Configure FIREBASE_SERVICE_ACCOUNT_JSON, FIREBASE_SERVICE_ACCOUNT_PATH ou '
            'salve a credencial em %LOCALAPPDATA%\\Antimary\\firebase-service-account.json.'
        )
    if not credential_json and not Path(credential_path).is_file():
        raise FirebaseConfigurationError(
            'O arquivo da credencial Firebase não foi encontrado no caminho configurado.'
        )

    try:
        app = firebase_admin.get_app()
    except ValueError:
        try:
            if credential_json:
                service_account = json.loads(credential_json)
                if not isinstance(service_account, dict):
                    raise ValueError('A credencial deve ser um objeto JSON.')
                app_credential = credentials.Certificate(service_account)
            else:
                app_credential = credentials.Certificate(credential_path)
            app = firebase_admin.initialize_app(app_credential)
        except (OSError, TypeError, ValueError) as error:
            raise FirebaseConfigurationError(
                'Não foi possível carregar a credencial Firebase. Verifique a variável '
                'FIREBASE_SERVICE_ACCOUNT_JSON ou o caminho do arquivo.'
            ) from error
    return firestore.client(app=app)


def _json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _coordinates(value):
    if not isinstance(value, str):
        return None

    parts = value.split(',')
    if len(parts) != 2:
        return None
    try:
        latitude, longitude = (float(part.strip()) for part in parts)
    except ValueError:
        return None
    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return None
    return latitude, longitude


def _cloudinary_images(value):
    if not isinstance(value, list):
        return []

    images = []
    for image in value:
        if not isinstance(image, dict):
            continue
        url = image.get('url')
        if not isinstance(url, str):
            continue
        parsed_url = urlparse(url)
        if parsed_url.scheme != 'https' or parsed_url.hostname != 'res.cloudinary.com':
            continue
        images.append({
            'url': url,
            'name': str(image.get('nome') or 'Imagem da coleta'),
            'type': str(image.get('tipo') or ''),
        })
    return images


def _morador_title(data):
    return str(data.get('nome') or 'Morador sem nome informado')


def _morador_fields(data):
    return [
        {'label': label, 'value': _json_value(data[field])}
        for field, label in DISPLAY_FIELDS
        if data.get(field) not in (None, '', [])
    ]


def _morador_residents(data):
    residents = []
    if isinstance(data.get('moradores'), list):
        for resident in data['moradores']:
            if not isinstance(resident, dict):
                continue
            fields = [
                {'label': label, 'value': _json_value(resident[field])}
                for field, label in RESIDENT_FIELDS
                if resident.get(field) not in (None, '', [])
            ]
            residents.append({
                'name': str(resident.get('nome') or 'Morador sem nome informado'),
                'fields': fields,
            })
    return residents


def _morador_record(document):
    data = document.to_dict() or {}
    coordinates = _coordinates(data.get('localizacao'))
    if not coordinates:
        return None

    latitude, longitude = coordinates
    return {
        'id': document.id,
        'latitude': latitude,
        'longitude': longitude,
        'title': _morador_title(data),
        'fields': _morador_fields(data),
        'residents': _morador_residents(data),
        'images': _cloudinary_images(data.get('imagens')),
    }


def get_moradores():
    client = _get_firestore_client()
    try:
        records = []
        for document in client.collection('moradores').stream():
            record = _morador_record(document)
            if record:
                records.append(record)
    except GoogleAPICallError as error:
        raise FirebaseUnavailable(
            'Não foi possível consultar os dados de moradores no Firestore.'
        ) from error
    return records


def get_morador_detail(record_id):
    client = _get_firestore_client()
    try:
        document = client.collection('moradores').document(record_id).get()
    except GoogleAPICallError as error:
        raise FirebaseUnavailable(
            'Não foi possível consultar os detalhes do cadastro no Firestore.'
        ) from error

    if not document.exists:
        return None

    data = document.to_dict() or {}
    coordinates = _coordinates(data.get('localizacao'))
    return {
        'id': document.id,
        'title': _morador_title(data),
        'coordinates': (
            {'latitude': coordinates[0], 'longitude': coordinates[1]}
            if coordinates
            else None
        ),
        'fields': _morador_fields(data),
        'residents': _morador_residents(data),
        'images': _cloudinary_images(data.get('imagens')),
    }


def get_cadastros_summary():
    client = _get_firestore_client()
    records = []
    colonies = {}
    genders = {}
    linked_residents = 0

    try:
        for document in client.collection('moradores').stream():
            data = document.to_dict() or {}
            resident_data = data.get('moradores')
            residents = (
                [resident for resident in resident_data if isinstance(resident, dict)]
                if isinstance(resident_data, list)
                else []
            )
            colony = data.get('colonia')
            colony = str(colony).strip() if colony not in (None, '') else 'Não informada'
            registered_at = data.get('registrado_em')
            if isinstance(registered_at, (datetime, date)):
                registered_at = _json_value(registered_at)
            elif registered_at is not None:
                registered_at = str(registered_at)
            records.append({
                'id': document.id,
                'name': str(data.get('nome') or 'Morador sem nome informado'),
                'colony': colony,
                'registered_at': _json_value(registered_at),
                'linked_residents': len(residents),
            })
            colonies[colony] = colonies.get(colony, 0) + 1
            linked_residents += len(residents)

            for resident in residents:
                gender = resident.get('genero')
                gender = str(gender).strip() if gender not in (None, '') else 'Não informado'
                genders[gender] = genders.get(gender, 0) + 1
    except GoogleAPICallError as error:
        raise FirebaseUnavailable(
            'Não foi possível consultar os dados de moradores no Firestore.'
        ) from error

    return {
        'records': records,
        'total_records': len(records),
        'linked_residents': linked_residents,
        'by_colony': [
            {'label': label, 'count': count}
            for label, count in sorted(
                colonies.items(),
                key=lambda item: (-item[1], item[0].casefold()),
            )
        ],
        'residents_by_gender': [
            {'label': label, 'count': count}
            for label, count in sorted(
                genders.items(),
                key=lambda item: (-item[1], item[0].casefold()),
            )
        ],
    }
