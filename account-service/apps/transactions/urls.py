from django.urls import path

from apps.transactions.views import (
    InternalTransactionStatusUpdateView,
    TransactionDetailView,
    TransactionListCreateView,
)

urlpatterns = [
    path("transactions/", TransactionListCreateView.as_view(), name="transaction-list-create"),
    path("transactions/<uuid:pk>/", TransactionDetailView.as_view(), name="transaction-detail"),
    path(
        "internal/transactions/<uuid:pk>/status/",
        InternalTransactionStatusUpdateView.as_view(),
        name="internal-transaction-status-update",
    ),
]
