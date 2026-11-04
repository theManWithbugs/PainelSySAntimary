import logging
import secrets

from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from mapa.firebase_data import (
    FirebaseConfigurationError,
    FirebaseUnavailable,
    get_cadastros_summary,
    get_morador_detail,
    get_moradores,
)


logger = logging.getLogger(__name__)
MAP_ACCESS_PIN = '1242'
MAP_ACCESS_SESSION_KEY = 'map_access_granted'


def health_check(request):
    return HttpResponse('ok')


def home(request):
    if request.session.get(MAP_ACCESS_SESSION_KEY):
        return render(request, 'mapa/home.html')

    error = None
    if request.method == 'POST':
        pin = request.POST.get('pin', '')
        if len(pin) == 4 and pin.isascii() and pin.isdigit() and secrets.compare_digest(
            pin, MAP_ACCESS_PIN
        ):
            request.session.cycle_key()
            request.session[MAP_ACCESS_SESSION_KEY] = True
            return redirect('home')
        error = 'PIN inválido. Confira os quatro dígitos e tente novamente.'

    response = render(request, 'mapa/pin.html', {'error': error})
    response['Cache-Control'] = 'no-store'
    return response


def indicadores(request):
    if not request.session.get(MAP_ACCESS_SESSION_KEY):
        return redirect('home')
    response = render(request, 'mapa/indicadores.html')
    response['Cache-Control'] = 'no-store'
    return response


def moradores_api(request):
    if not request.session.get(MAP_ACCESS_SESSION_KEY):
        return JsonResponse(
            {'error': 'Informe o PIN para acessar os dados do mapa.'},
            status=403,
            headers={'Cache-Control': 'no-store'},
        )

    try:
        return JsonResponse({'moradores': get_moradores()}, headers={'Cache-Control': 'no-store'})
    except (FirebaseConfigurationError, FirebaseUnavailable) as error:
        logger.exception('Não foi possível carregar os moradores do Firestore.')
        return JsonResponse(
            {'error': str(error)},
            status=503,
            headers={'Cache-Control': 'no-store'},
        )


def indicadores_api(request):
    if not request.session.get(MAP_ACCESS_SESSION_KEY):
        return JsonResponse(
            {'error': 'Informe o PIN para acessar os dados do mapa.'},
            status=403,
            headers={'Cache-Control': 'no-store'},
        )

    try:
        return JsonResponse(get_cadastros_summary(), headers={'Cache-Control': 'no-store'})
    except (FirebaseConfigurationError, FirebaseUnavailable) as error:
        logger.exception('Não foi possível carregar o resumo dos cadastros do Firestore.')
        return JsonResponse(
            {'error': str(error)},
            status=503,
            headers={'Cache-Control': 'no-store'},
        )


def morador_detail_api(request, record_id):
    if not request.session.get(MAP_ACCESS_SESSION_KEY):
        return JsonResponse(
            {'error': 'Informe o PIN para acessar os dados do mapa.'},
            status=403,
            headers={'Cache-Control': 'no-store'},
        )

    try:
        record = get_morador_detail(record_id)
    except (FirebaseConfigurationError, FirebaseUnavailable) as error:
        logger.exception('Não foi possível carregar os detalhes do cadastro %s.', record_id)
        return JsonResponse(
            {'error': str(error)},
            status=503,
            headers={'Cache-Control': 'no-store'},
        )

    if record is None:
        return JsonResponse(
            {'error': 'O cadastro solicitado não foi encontrado.'},
            status=404,
            headers={'Cache-Control': 'no-store'},
        )
    return JsonResponse(record, headers={'Cache-Control': 'no-store'})
