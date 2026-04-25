from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.documents.models import Document
from tests.factories import UserFactory


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _pdf_file(size: int = 1024, name: str = "test.pdf") -> SimpleUploadedFile:
    """Return a fake PDF upload of the given byte size."""
    return SimpleUploadedFile(name, b"%PDF-" + b"x" * (size - 5), content_type="application/pdf")


# ---------------------------------------------------------------------------
# Upload tests
# ---------------------------------------------------------------------------

@patch("apps.documents.views.upload_file", return_value="fake-object-key")
@patch("apps.documents.views.ensure_bucket")
def test_upload_valid_pdf_returns_201(mock_ensure, mock_upload, auth_client: APIClient) -> None:
    file = _pdf_file()
    response = auth_client.post("/api/documents/", {"file": file}, format="multipart")

    assert response.status_code == 201
    assert "id" in response.data
    assert "file_name" in response.data
    assert response.data["file_name"] == "test.pdf"
    assert response.data["file_type"] == "application/pdf"
    mock_ensure.assert_called_once()
    mock_upload.assert_called_once()


@patch("apps.documents.views.upload_file", return_value="fake-object-key")
@patch("apps.documents.views.ensure_bucket")
def test_upload_oversized_file_returns_400(mock_ensure, mock_upload, auth_client: APIClient) -> None:
    # MAX_SIZE_BYTES = 10 MB — create a file just over the limit
    from integrations.storage.minio_client import MAX_SIZE_BYTES

    oversized_file = SimpleUploadedFile(
        "big.pdf",
        b"%PDF-" + b"x" * MAX_SIZE_BYTES,  # one byte over
        content_type="application/pdf",
    )
    response = auth_client.post("/api/documents/", {"file": oversized_file}, format="multipart")

    assert response.status_code == 400
    assert "error" in response.data
    mock_upload.assert_not_called()


@patch("apps.documents.views.upload_file", return_value="fake-object-key")
@patch("apps.documents.views.ensure_bucket")
def test_upload_invalid_content_type_returns_400(mock_ensure, mock_upload, auth_client: APIClient) -> None:
    file = SimpleUploadedFile("script.py", b"print('hi')", content_type="text/x-python")
    response = auth_client.post("/api/documents/", {"file": file}, format="multipart")

    assert response.status_code == 400
    assert "error" in response.data
    mock_upload.assert_not_called()


def test_upload_no_file_returns_400(auth_client: APIClient) -> None:
    response = auth_client.post("/api/documents/", {}, format="multipart")

    assert response.status_code == 400
    assert "error" in response.data


# ---------------------------------------------------------------------------
# Download tests
# ---------------------------------------------------------------------------

@patch("apps.documents.views.get_presigned_url", return_value="https://minio/presigned")
def test_download_own_document_returns_presigned_url(mock_presigned, auth_client: APIClient, user) -> None:
    doc = Document.objects.create(
        user=user,
        file_name="receipt.pdf",
        file_type="application/pdf",
        file_size=1024,
        bucket_name="finflow-documents",
        object_key="abc-123",
    )

    response = auth_client.get(f"/api/documents/{doc.id}/download/")

    assert response.status_code == 200
    assert response.data["url"] == "https://minio/presigned"
    assert response.data["expires_in"] == 900
    mock_presigned.assert_called_once_with("finflow-documents", "abc-123", 900)


def test_download_other_users_document_returns_404(auth_client: APIClient) -> None:
    other_user = UserFactory()
    doc = Document.objects.create(
        user=other_user,
        file_name="private.pdf",
        file_type="application/pdf",
        file_size=512,
        bucket_name="finflow-documents",
        object_key="xyz-999",
    )

    response = auth_client.get(f"/api/documents/{doc.id}/download/")

    # Must be 404 — not 403 — to avoid leaking resource existence
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# List test
# ---------------------------------------------------------------------------

@patch("apps.documents.views.upload_file", return_value="key1")
@patch("apps.documents.views.ensure_bucket")
def test_list_documents_returns_own_only(mock_ensure, mock_upload, auth_client: APIClient, user) -> None:
    # Own document
    Document.objects.create(
        user=user,
        file_name="mine.pdf",
        file_type="application/pdf",
        file_size=1024,
        bucket_name="finflow-documents",
        object_key="mine-key",
    )
    # Another user's document
    other_user = UserFactory()
    Document.objects.create(
        user=other_user,
        file_name="theirs.pdf",
        file_type="application/pdf",
        file_size=2048,
        bucket_name="finflow-documents",
        object_key="their-key",
    )

    response = auth_client.get("/api/documents/")

    assert response.status_code == 200
    names = {item["file_name"] for item in response.data["results"]}
    assert "mine.pdf" in names
    assert "theirs.pdf" not in names
    assert len(names) == 1
