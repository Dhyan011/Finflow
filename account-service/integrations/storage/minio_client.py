from datetime import timedelta
from io import BytesIO
from typing import Final
from uuid import uuid4

from django.conf import settings
from minio import Minio

ALLOWED_CONTENT_TYPES: Final[set[str]] = {"application/pdf", "image/png", "image/jpeg"}
MAX_SIZE_BYTES: Final[int] = 10 * 1024 * 1024

_minio_client: Minio | None = None


def get_minio_client() -> Minio:
    global _minio_client
    if _minio_client is None:
        _minio_client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
    return _minio_client


def ensure_bucket(bucket: str) -> None:
    client = get_minio_client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)


def upload_file(bucket: str, data: bytes, content_type: str) -> str:
    client = get_minio_client()
    object_key = str(uuid4())
    data_stream = BytesIO(data)
    client.put_object(
        bucket_name=bucket,
        object_name=object_key,
        data=data_stream,
        length=len(data),
        content_type=content_type,
    )
    return object_key


def get_presigned_url(bucket: str, object_key: str, expires_seconds: int = 900) -> str:
    client = get_minio_client()
    return client.presigned_get_object(
        bucket_name=bucket,
        object_name=object_key,
        expires=timedelta(seconds=expires_seconds),
    )
