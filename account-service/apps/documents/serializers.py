from rest_framework import serializers

from apps.documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ("id", "file_name", "file_type", "file_size", "uploaded_at")
        read_only_fields = ("id", "uploaded_at")


class DocumentDownloadSerializer(serializers.Serializer):
    url = serializers.URLField()
    expires_in = serializers.IntegerField()
