from django.urls import path

from apps.accounts.views import AccountDetailView, AccountListCreateView

urlpatterns = [
    path("accounts/", AccountListCreateView.as_view(), name="account-list-create"),
    path("accounts/<uuid:pk>/", AccountDetailView.as_view(), name="account-detail"),
]
