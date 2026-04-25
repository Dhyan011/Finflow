from unittest.mock import patch

from rest_framework.test import APIClient

from apps.transactions.models import Transaction
from tests.factories import AccountFactory, TransactionFactory, UserFactory


def test_create_transaction_status_is_pending(auth_client: APIClient, account) -> None:
    response = auth_client.post(
        "/api/transactions/",
        {
            "account": str(account.id),
            "amount": "99.99",
            "currency": "USD",
            "direction": "CREDIT",
        },
        format="json",
    )

    assert response.status_code == 201
    assert response.data["status"] == Transaction.Status.PENDING


def test_create_transaction_with_wrong_account_returns_403_or_400(auth_client: APIClient) -> None:
    other_account = AccountFactory()
    response = auth_client.post(
        "/api/transactions/",
        {
            "account": str(other_account.id),
            "amount": "10.00",
            "currency": "USD",
            "direction": "DEBIT",
        },
        format="json",
    )
    assert response.status_code in {400, 403}


def test_list_transactions_returns_own_only(auth_client: APIClient, user) -> None:
    own_transaction = TransactionFactory(account__user=user)
    TransactionFactory()

    response = auth_client.get("/api/transactions/")

    assert response.status_code == 200
    ids = {item["id"] for item in response.data["results"]}
    assert str(own_transaction.id) in ids
    assert len(ids) == 1


@patch("integrations.kafka.producer.publish_event")
def test_kafka_publish_called_on_create(mock_publish_event, auth_client: APIClient, account) -> None:
    response = auth_client.post(
        "/api/transactions/",
        {
            "account": str(account.id),
            "amount": "12.34",
            "currency": "USD",
            "direction": "CREDIT",
        },
        format="json",
    )

    assert response.status_code == 201
    mock_publish_event.assert_called_once()


@patch("integrations.kafka.producer.get_producer", side_effect=Exception("kafka_down"))
def test_transaction_created_even_when_kafka_fails(_mock_get_producer, auth_client: APIClient, account) -> None:
    response = auth_client.post(
        "/api/transactions/",
        {
            "account": str(account.id),
            "amount": "12.34",
            "currency": "USD",
            "direction": "DEBIT",
        },
        format="json",
    )

    assert response.status_code == 201
    assert Transaction.objects.filter(id=response.data["id"]).exists() is True


def test_internal_status_update_pending_to_completed(db) -> None:
    transaction = TransactionFactory(status=Transaction.Status.PENDING)
    client = APIClient()

    response = client.patch(
        f"/api/internal/transactions/{transaction.id}/status/",
        {"status": "COMPLETED", "reference": "REF-OK"},
        format="json",
    )

    assert response.status_code == 200
    transaction.refresh_from_db()
    assert transaction.status == Transaction.Status.COMPLETED


def test_internal_status_update_invalid_transition_returns_422(db) -> None:
    transaction = TransactionFactory(status=Transaction.Status.COMPLETED)
    client = APIClient()

    response = client.patch(
        f"/api/internal/transactions/{transaction.id}/status/",
        {"status": "FAILED"},
        format="json",
    )

    assert response.status_code == 422
    assert response.data == {"error": "invalid_transition"}


# ---------------------------------------------------------------------------
# Additional tests to close coverage gaps
# ---------------------------------------------------------------------------

def test_list_transactions_filter_by_account(auth_client: APIClient, user) -> None:
    """Covers get_queryset() account filter branch (line 36)."""
    txn1 = TransactionFactory(account__user=user)
    txn2 = TransactionFactory(account__user=user)

    response = auth_client.get(f"/api/transactions/?account={txn1.account_id}")

    assert response.status_code == 200
    ids = {item["id"] for item in response.data["results"]}
    assert str(txn1.id) in ids
    assert str(txn2.id) not in ids


def test_list_transactions_filter_by_status(auth_client: APIClient, user) -> None:
    """Covers get_queryset() status filter branch (line 38)."""
    pending_txn = TransactionFactory(account__user=user, status=Transaction.Status.PENDING)
    completed_txn = TransactionFactory(account__user=user, status=Transaction.Status.COMPLETED)

    response = auth_client.get("/api/transactions/?status=PENDING")

    assert response.status_code == 200
    ids = {item["id"] for item in response.data["results"]}
    assert str(pending_txn.id) in ids
    assert str(completed_txn.id) not in ids


def test_transaction_detail_returns_own(auth_client: APIClient, user) -> None:
    """Covers TransactionDetailView happy path (line 66)."""
    txn = TransactionFactory(account__user=user)

    response = auth_client.get(f"/api/transactions/{txn.id}/")

    assert response.status_code == 200
    assert str(response.data["id"]) == str(txn.id)


def test_transaction_detail_by_other_user_returns_403(db) -> None:
    """Covers TransactionDetailView.get_object() PermissionDenied branch (lines 69-72)."""
    owner = UserFactory()
    intruder = UserFactory()
    txn = TransactionFactory(account__user=owner)
    client = APIClient()
    client.force_authenticate(user=intruder)

    response = client.get(f"/api/transactions/{txn.id}/")

    assert response.status_code == 403


def test_internal_status_update_same_status_is_idempotent(db) -> None:
    """Covers idempotent early-return branch (line 87): same status → 200."""
    transaction = TransactionFactory(status=Transaction.Status.COMPLETED)
    client = APIClient()

    response = client.patch(
        f"/api/internal/transactions/{transaction.id}/status/",
        {"status": "COMPLETED"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == Transaction.Status.COMPLETED


@patch("integrations.kafka.producer.get_producer", side_effect=Exception("kafka_down"))
def test_internal_status_update_kafka_fail_still_saves(_mock, db) -> None:
    """Covers Kafka error-log path in InternalTransactionStatusUpdateView (lines 104-105)."""
    transaction = TransactionFactory(status=Transaction.Status.PENDING)
    client = APIClient()

    response = client.patch(
        f"/api/internal/transactions/{transaction.id}/status/",
        {"status": "COMPLETED", "reference": "REF-KAFKA-FAIL"},
        format="json",
    )

    assert response.status_code == 200
    transaction.refresh_from_db()
    assert transaction.status == Transaction.Status.COMPLETED
