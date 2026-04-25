from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.users.views import UserMeView, UserRegistrationView

urlpatterns = [
    path("auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("users/", UserRegistrationView.as_view(), name="user-register"),
    path("users/me/", UserMeView.as_view(), name="user-me"),
]
