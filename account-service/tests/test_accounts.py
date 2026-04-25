from apps.accounts.models import Account
from rest_framework.test import APIClient

from tests.factories import AccountFactory, UserFactory


def test_create_account_returns_201(auth_client: APIClient) -> None:
    response = auth_client.post("/api/accounts/", {"currency": "USD"}, format="json")
    assert response.status_code == 201


def test_account_number_auto_generated_with_acc_prefix(auth_client: APIClient) -> None:
    response = auth_client.post("/api/accounts/", {"currency": "USD"}, format="json")
    assert response.status_code == 201
    assert response.data["account_number"].startswith("ACC")


def test_list_accounts_returns_only_own(auth_client: APIClient, user) -> None:
    AccountFactory(user=user)
    AccountFactory()

    response = auth_client.get("/api/accounts/")

    assert response.status_code == 200
    assert len(response.data["results"]) == 1


def test_get_account_by_other_user_returns_403(db) -> None:
    owner = UserFactory()
    intruder = UserFactory()
    account = AccountFactory(user=owner)
    client = APIClient()
    client.force_authenticate(user=intruder)

    response = client.get(f"/api/accounts/{account.id}/")

    assert response.status_code == 403


def test_soft_delete_account(auth_client: APIClient, account) -> None:
    response = auth_client.delete(f"/api/accounts/{account.id}/")

    assert response.status_code == 204


def test_patch_account_status(auth_client: APIClient, account) -> None:
    """Covers AccountDetailView.get_serializer_class() PATCH branch (lines 28-30)."""
    response = auth_client.patch(
        f"/api/accounts/{account.id}/",
        {"status": Account.Status.SUSPENDED},
        format="json",
    )
    assert response.status_code == 200
    account.refresh_from_db()
    assert account.status == Account.Status.SUSPENDED


def test_patch_account_by_other_user_returns_403(db) -> None:
    owner = UserFactory()
    intruder = UserFactory()
    account = AccountFactory(user=owner)
    client = APIClient()
    client.force_authenticate(user=intruder)

    response = client.patch(
        f"/api/accounts/{account.id}/",
        {"status": "SUSPENDED"},
        format="json",
    )
    assert response.status_code == 403

