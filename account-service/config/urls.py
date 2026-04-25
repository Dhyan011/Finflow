from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def healthcheck(_request):
    return JsonResponse({"status": "ok"})


urlpatterns = [
    path("health/", healthcheck, name="healthcheck"),
    path("api/", include("apps.users.urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.transactions.urls")),
    path("api/", include("apps.documents.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/schema/swagger-ui/", SpectacularSwaggerView.as_view(url_name="schema")),
]
