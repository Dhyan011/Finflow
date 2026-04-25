import logging
import uuid

import pytest
from rest_framework.test import APIClient

from apps.core.logging import PIIScrubFilter
from apps.users.models import User

# ---------------------------------------------------------------------------
# Model-level tests (Day 1)
# ---------------------------------------------------------------------------


def test_user_created_with_uuid_pk(user) -> None:
    parsed_uuid = uuid.UUID(str(user.id))
    assert parsed_uuid.version in {1, 2, 3, 4, 5}


def test_soft_delete(user) -> None:
    user_id = user.id
    user.soft_delete()

    assert User.all_objects.get(id=user_id).is_deleted is True
    assert User.objects.filter(id=user_id).exists() is False
    assert User.all_objects.filter(id=user_id).exists() is True


def test_user_requires_email() -> None:
    with pytest.raises(ValueError):
        User.objects.create_user(email="", password="testpass123", full_name="No Email")


def test_pii_scrub_filter_masks_email_in_message() -> None:
    pii_filter = PIIScrubFilter()
    record = logging.LogRecord(
        name="finflow",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="login from user test.user@example.com was successful",
        args=(),
        exc_info=None,
    )

    allowed = pii_filter.filter(record)

    assert allowed is True
    assert "[email]" in record.msg
    assert "test.user@example.com" not in record.msg


def test_pii_scrub_filter_redacts_pii_attributes() -> None:
    """Covers apps/core/logging.py line 15 — setattr(record, field, '***')."""
    pii_filter = PIIScrubFilter()
    record = logging.LogRecord(
        name="finflow",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="user action",
        args=(),
        exc_info=None,
    )
    # Attach a PII field as an extra attribute (as Django logging does)
    record.token = "super-secret-jwt-token"
    record.password = "hunter2"

    allowed = pii_filter.filter(record)

    assert allowed is True
    assert record.token == "***"
    assert record.password == "***"


# ---------------------------------------------------------------------------
# API-level tests for UserRegistrationView (Task 2.1)
# ---------------------------------------------------------------------------


def test_register_user_returns_201(api_client: APIClient, db) -> None:
    response = api_client.post(
        "/api/users/",
        {
            "email": "new@example.com",
            "full_name": "New User",
            "password": "securepass123",
        },
        format="json",
    )
    assert response.status_code == 201
    assert response.data["email"] == "new@example.com"
    assert "password" not in response.data  # must be write-only


def test_register_duplicate_email_returns_400(api_client: APIClient, user) -> None:
    response = api_client.post(
        "/api/users/",
        {"email": user.email, "full_name": "Duplicate", "password": "securepass123"},
        format="json",
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# API-level tests for UserMeView (Task 2.1)
# ---------------------------------------------------------------------------


def test_get_me_returns_own_profile(auth_client: APIClient, user) -> None:
    response = auth_client.get("/api/users/me/")
    assert response.status_code == 200
    assert response.data["email"] == user.email
    assert response.data["full_name"] == user.full_name


def test_patch_me_updates_full_name(auth_client: APIClient, user) -> None:
    response = auth_client.patch(
        "/api/users/me/",
        {"full_name": "Updated Name"},
        format="json",
    )
    assert response.status_code == 200
    assert response.data["full_name"] == "Updated Name"
    user.refresh_from_db()
    assert user.full_name == "Updated Name"


def test_patch_me_cannot_change_email(auth_client: APIClient, user) -> None:
    """email is read_only in UserProfileSerializer — should be silently ignored."""
    original_email = user.email
    response = auth_client.patch(
        "/api/users/me/",
        {"email": "hacker@evil.com"},
        format="json",
    )
    assert response.status_code == 200
    user.refresh_from_db()
    assert user.email == original_email  # unchanged


def test_delete_me_soft_deletes_account(auth_client: APIClient, user) -> None:
    user_id = user.id
    response = auth_client.delete("/api/users/me/")
    assert response.status_code == 204
    # User is soft-deleted: all_objects still finds it, objects doesn't
    assert User.all_objects.get(id=user_id).is_deleted is True
    assert User.objects.filter(id=user_id).exists() is False


def test_unauthenticated_get_me_returns_401(api_client: APIClient, db) -> None:
    response = api_client.get("/api/users/me/")
    assert response.status_code == 401
