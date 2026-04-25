import logging

from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer
from integrations.storage.minio_client import (
    ALLOWED_CONTENT_TYPES,
    MAX_SIZE_BYTES,
    ensure_bucket,
    get_presigned_url,
    upload_file,
)

logger = logging.getLogger(__name__)

BUCKET = "finflow-documents"
PRESIGNED_URL_EXPIRY = 900  # seconds


class DocumentUploadView(generics.ListCreateAPIView):
    """
    POST  /api/documents/  — upload a document (multipart/form-data)
    GET   /api/documents/  — list own documents (paginated)
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DocumentSerializer

    # Only POST uses multipart; GET falls back to default parsers.
    parser_classes = [MultiPartParser]

    def get_queryset(self):
        return Document.objects.filter(user=self.request.user)

    def create(self, request: Request, *args, **kwargs) -> Response:
        file = request.FILES.get("file")

        if not file:
            return Response(
                {"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST
            )

        if file.content_type not in ALLOWED_CONTENT_TYPES:
            return Response(
                {
                    "error": (
                        f"Unsupported file type '{file.content_type}'. "
                        f"Allowed: {sorted(ALLOWED_CONTENT_TYPES)}"
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if file.size > MAX_SIZE_BYTES:
            return Response(
                {"error": f"File exceeds maximum size of {MAX_SIZE_BYTES} bytes."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = file.read()
        ensure_bucket(BUCKET)
        object_key = upload_file(BUCKET, data, file.content_type)

        document = Document.objects.create(
            user=request.user,
            file_name=file.name,
            file_type=file.content_type,
            file_size=file.size,
            bucket_name=BUCKET,
            object_key=object_key,
        )

        serializer = DocumentSerializer(document)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class DocumentDownloadView(APIView):
    """
    GET /api/documents/<id>/download/
    Returns a presigned URL valid for 15 minutes.
    Returns 404 (not 403) if document is not owned by the requesting user —
    to avoid leaking resource existence.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk) -> Response:
        try:
            document = Document.objects.get(pk=pk)
        except Document.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        # Ownership check: return 404 to avoid leaking existence
        if document.user_id != request.user.id:
            return Response(status=status.HTTP_404_NOT_FOUND)

        presigned_url = get_presigned_url(
            document.bucket_name, document.object_key, PRESIGNED_URL_EXPIRY
        )
        return Response(
            {"url": presigned_url, "expires_in": PRESIGNED_URL_EXPIRY},
            status=status.HTTP_200_OK,
        )
