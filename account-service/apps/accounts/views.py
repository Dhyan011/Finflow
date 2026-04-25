from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated

from apps.accounts.models import Account
from apps.accounts.serializers import AccountSerializer, AccountStatusUpdateSerializer
from apps.core.audit import log_audit


class AccountListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer

    @extend_schema(
        examples=[
            OpenApiExample(
                "Valid Account Creation",
                value={"currency": "USD"},
                request_only=True,
            ),
        ]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        account = serializer.save(user=self.request.user)
        log_audit(
            user=self.request.user,
            action="CREATE",
            resource_type="Account",
            resource_id=account.id,
            after={"status": account.status, "currency": account.currency},
            request=self.request,
        )


class AccountDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = Account.objects.all()

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return AccountStatusUpdateSerializer
        return AccountSerializer

    def get_object(self) -> Account:
        account = get_object_or_404(Account.objects.all(), id=self.kwargs["pk"])
        if account.user_id != self.request.user.id:
            raise PermissionDenied("You do not have permission to access this account.")
        return account

    def perform_update(self, serializer):
        account = self.get_object()
        before_state = {"status": account.status}
        updated_account = serializer.save()
        log_audit(
            user=self.request.user,
            action="UPDATE",
            resource_type="Account",
            resource_id=updated_account.id,
            before=before_state,
            after={"status": updated_account.status},
            request=self.request,
        )

    def perform_destroy(self, instance):
        log_audit(
            user=self.request.user,
            action="DELETE",
            resource_type="Account",
            resource_id=instance.id,
            before={"status": instance.status},
            request=self.request,
        )
        instance.soft_delete()
