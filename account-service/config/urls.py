from django.http import JsonResponse
from django.urls import include, path


def healthcheck(_request):
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('health/', healthcheck, name='healthcheck'),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.transactions.urls")),
    path("api/", include("apps.documents.urls")),
]
