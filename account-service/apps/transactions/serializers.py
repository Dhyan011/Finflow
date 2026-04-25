from rest_framework import serializers

from apps.accounts.models import Account
from apps.transactions.models import Transaction


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = (
            "id",
            "account",
            "amount",
            "currency",
            "direction",
            "status",
            "reference",
            "metadata",
            "created_at",
        )
        read_only_fields = ("id", "status", "created_at")

    def validate_account(self, account: Account) -> Account:
        request = self.context["request"]
        if account.user_id != request.user.id:
            raise serializers.ValidationError("Account does not belong to user.")
        return account


class InternalTransactionStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[Transaction.Status.COMPLETED, Transaction.Status.FAILED]
    )
    reference = serializers.CharField(required=False, allow_blank=True, max_length=255)
