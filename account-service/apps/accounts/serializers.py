from rest_framework import serializers

from apps.accounts.models import Account


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = (
            "id",
            "account_number",
            "balance",
            "currency",
            "status",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "account_number",
            "balance",
            "created_at",
            "updated_at",
        )


class AccountStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ("status",)
