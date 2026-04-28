import logging
import os
import threading
import httpx

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.audit import log_audit
from apps.core.hmac_utils import generate_signature
from apps.transactions.models import Transaction
from apps.transactions.serializers import (
    InternalTransactionStatusSerializer,
    TransactionSerializer,
)

logger = logging.getLogger(__name__)

VALID_TRANSITIONS = {
    Transaction.Status.PENDING: {
        Transaction.Status.COMPLETED,
        Transaction.Status.FAILED,
    }
}


class TransactionListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    @extend_schema(
        examples=[
            OpenApiExample(
                "Valid Transaction",
                value={
                    "account": "00000000-0000-0000-0000-000000000000",
                    "amount": "100.00",
                    "currency": "USD",
                    "direction": "CREDIT",
                },
                request_only=True,
            ),
        ]
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Transaction.objects.filter(account__user=self.request.user)
        account_id = self.request.query_params.get("account")
        status_value = self.request.query_params.get("status")
        if account_id:
            queryset = queryset.filter(account_id=account_id)
        if status_value:
            queryset = queryset.filter(status=status_value)
        return queryset

    def perform_create(self, serializer: TransactionSerializer) -> None:
        transaction = serializer.save(status=Transaction.Status.PENDING)
        log_audit(
            user=self.request.user,
            action="CREATE",
            resource_type="Transaction",
            resource_id=transaction.id,
            after={
                "status": transaction.status,
                "amount": str(transaction.amount),
                "direction": transaction.direction,
                "account_id": str(transaction.account_id),
            },
            request=self.request,
        )
        payload = {
            "id": str(transaction.id),
            "account_id": str(transaction.account_id),
            "amount": str(transaction.amount),
            "currency": transaction.currency,
            "direction": transaction.direction,
        }
        try:
            from integrations.kafka.producer import publish_event

            publish_event("transaction.created", payload)
        except Exception as exc:
            logger.error(
                "kafka_publish_failed",
                extra={"topic": "transaction.created", "error": str(exc)},
            )
            
        # Trigger processing service asynchronously
        def _trigger_processing():
            processing_url = os.environ.get("PROCESSING_SERVICE_URL", "http://localhost:8001/api/process/")
            import json
            process_payload = {
                "transaction_id": str(transaction.id),
                "amount": float(transaction.amount),
                "currency": transaction.currency,
                "direction": transaction.direction,
            }
            raw_body = json.dumps(process_payload, separators=(",", ":"))
            headers = {"X-Signature": generate_signature(raw_body)}
            
            try:
                # Fire and forget
                httpx.post(processing_url, content=raw_body, headers=headers, timeout=5.0)
            except Exception as e:
                logger.error("processing_service_trigger_failed", extra={"transaction_id": str(transaction.id), "error": str(e)})

        threading.Thread(target=_trigger_processing, daemon=True).start()


class TransactionDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        return Transaction.objects.filter(account__user=self.request.user)

    def get_object(self) -> Transaction:
        transaction = get_object_or_404(Transaction.objects.all(), id=self.kwargs["pk"])
        if transaction.account.user_id != self.request.user.id:
            raise PermissionDenied(
                "You do not have permission to access this transaction."
            )
        return transaction


class InternalTransactionStatusUpdateView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=InternalTransactionStatusSerializer,
        responses={200: TransactionSerializer, 422: None},
    )
    def patch(self, request: Request, pk) -> Response:
        transaction = get_object_or_404(Transaction.all_objects.all(), id=pk)
        serializer = InternalTransactionStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status = serializer.validated_data["status"]
        reference = serializer.validated_data.get("reference", "")

        if transaction.status == new_status:
            return Response(
                TransactionSerializer(transaction).data, status=status.HTTP_200_OK
            )

        allowed = VALID_TRANSITIONS.get(transaction.status, set())
        if new_status not in allowed:
            return Response({"error": "invalid_transition"}, status=422)

        old_status = transaction.status
        transaction.status = new_status
        transaction.reference = reference
        transaction.save(update_fields=["status", "reference", "updated_at"])

        log_audit(
            user=request.user
            if request.user and request.user.is_authenticated
            else None,
            action="UPDATE",
            resource_type="Transaction",
            resource_id=transaction.id,
            before={"status": old_status},
            after={"status": transaction.status, "reference": transaction.reference},
            request=request,
        )

        try:
            from integrations.kafka.producer import publish_event

            publish_event(
                "transaction.updated",
                {"id": str(transaction.id), "status": transaction.status},
            )
        except Exception as exc:
            logger.error(
                "kafka_publish_failed",
                extra={"topic": "transaction.updated", "error": str(exc)},
            )

        return Response(
            TransactionSerializer(transaction).data, status=status.HTTP_200_OK
        )
