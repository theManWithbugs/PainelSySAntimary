import logging

from django.http import HttpResponse, JsonResponse
from django.shortcuts import render

from mapa.firebase_data import FirebaseConfigurationError, FirebaseUnavailable, get_moradores


logger = logging.getLogger(__name__)


def health_check(request):
    return HttpResponse('ok')


def home(request):
    return render(request, 'mapa/home.html')


def moradores_api(request):
    try:
        return JsonResponse({'moradores': get_moradores()}, headers={'Cache-Control': 'no-store'})
    except (FirebaseConfigurationError, FirebaseUnavailable) as error:
        logger.exception('Não foi possível carregar os moradores do Firestore.')
        return JsonResponse(
            {'error': str(error)},
            status=503,
            headers={'Cache-Control': 'no-store'},
        )
