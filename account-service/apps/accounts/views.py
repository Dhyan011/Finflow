from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from apps.accounts.models import Account
from apps.accounts.serializers import AccountSerializer, AccountStatusUpdateSerializer


class AccountListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AccountSerializer

    def get_queryset(self):
        return Account.objects.filter(user=self.request.user)

    def perform_create(self, serializer: AccountSerializer) -> None:
        serializer.save(user=self.request.user)


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

    def delete(self, request: Request, *args, **kwargs) -> Response:
        account = self.get_object()
        account.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
