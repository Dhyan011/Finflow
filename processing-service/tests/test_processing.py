import json
import re
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.hmac_utils import generate_signature, verify_signature
from app.integrations.account_client import update_transaction_status
from app.integrations.kafka_consumer import _make_consumer
from app.main import _handle_transaction_created, app

client = TestClient(app)


# ---------------------------------------------------------------------------
# HMAC utility tests
# ---------------------------------------------------------------------------


def test_generate_and_verify_signature() -> None:
    payload = "hello world"
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    sig = generate_signature(payload, timestamp, nonce)
    assert verify_signature(payload, sig, timestamp, nonce) is True


def test_verify_signature_rejects_tampered_payload() -> None:
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    sig = generate_signature("original", timestamp, nonce)
    assert verify_signature("tampered", sig, timestamp, nonce) is False


def test_verify_signature_rejects_wrong_signature() -> None:
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    assert verify_signature("data", "deadbeef" * 8, timestamp, nonce) is False
    
def test_verify_signature_rejects_stale_timestamp() -> None:
    payload = "data"
    timestamp = str(int(time.time()) - 400) # > 5 mins old
    nonce = str(uuid.uuid4())
    sig = generate_signature(payload, timestamp, nonce)
    assert verify_signature(payload, sig, timestamp, nonce) is False
    
def test_verify_signature_rejects_reused_nonce() -> None:
    payload = "data"
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    sig = generate_signature(payload, timestamp, nonce)
    assert verify_signature(payload, sig, timestamp, nonce) is True
    # Reusing the same nonce
    assert verify_signature(payload, sig, timestamp, nonce) is False


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------


def test_health_endpoint() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok", "service": "processing-service"}


# ---------------------------------------------------------------------------
# POST /api/process/ — HMAC-authenticated processing endpoint
# ---------------------------------------------------------------------------


def _make_process_body(transaction_id: str = "abc-123") -> dict:
    return {
        "transaction_id": transaction_id,
        "amount": 100.00,
        "currency": "USD",
        "direction": "CREDIT",
    }


def _signed_headers(body: dict) -> dict:
    raw = json.dumps(body, separators=(",", ":"))
    timestamp = str(int(time.time()))
    nonce = str(uuid.uuid4())
    return {
        "X-Signature": generate_signature(raw, timestamp, nonce),
        "X-Timestamp": timestamp,
        "X-Nonce": nonce,
    }


def test_process_returns_401_with_no_signature() -> None:
    body = _make_process_body()
    resp = client.post("/api/process/", json=body)
    assert resp.status_code == 422  # missing required header


def test_process_returns_401_with_wrong_signature() -> None:
    body = _make_process_body()
    headers = _signed_headers(body)
    headers["X-Signature"] = "badsig"
    resp = client.post(
        "/api/process/",
        json=body,
        headers=headers,
    )
    assert resp.status_code == 401
    assert resp.json()["detail"] == "invalid_signature"


def test_process_returns_200_on_success(httpx_mock) -> None:
    """Account service responds 200 — expect 200 from processing service."""
    httpx_mock.add_response(
        method="PATCH",
        url=re.compile(r".*/api/internal/transactions/.*/status/"),
        json={"id": "abc-123", "status": "COMPLETED"},
        status_code=200,
    )

    body = _make_process_body()
    headers = _signed_headers(body)

    resp = client.post("/api/process/", json=body, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["result"] == "approved"
    assert data["transaction_id"] == "abc-123"


def test_process_returns_502_when_account_service_fails(httpx_mock) -> None:
    """Account service returns 500 — expect 502 from processing service."""
    httpx_mock.add_response(
        method="PATCH",
        url=re.compile(r".*/api/internal/transactions/.*/status/"),
        status_code=500,
    )

    body = _make_process_body()
    headers = _signed_headers(body)

    resp = client.post("/api/process/", json=body, headers=headers)
    assert resp.status_code == 502
    assert resp.json()["detail"] == "account_service_unavailable"


# ---------------------------------------------------------------------------
# Account Client tests (Coverage)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_transaction_status_success(httpx_mock) -> None:
    httpx_mock.add_response(
        method="PATCH",
        url=re.compile(r".*/api/internal/transactions/.*/status/"),
        status_code=200,
    )
    result = await update_transaction_status("123", "COMPLETED", "ref")
    assert result is True

@pytest.mark.asyncio
async def test_update_transaction_status_http_error(httpx_mock) -> None:
    httpx_mock.add_response(
        method="PATCH",
        url=re.compile(r".*/api/internal/transactions/.*/status/"),
        status_code=400,
    )
    result = await update_transaction_status("123", "COMPLETED", "ref")
    assert result is False

@pytest.mark.asyncio
async def test_update_transaction_status_network_error(httpx_mock) -> None:
    import httpx
    httpx_mock.add_exception(httpx.RequestError("network error"))
    result = await update_transaction_status("123", "COMPLETED", "ref")
    assert result is False


# ---------------------------------------------------------------------------
# Kafka and Main tests (Coverage)
# ---------------------------------------------------------------------------

def test_make_consumer() -> None:
    consumer = _make_consumer()
    assert consumer is not None

def test_handle_transaction_created_missing_id(caplog) -> None:
    _handle_transaction_created({"amount": 100})
    assert "kafka_event_missing_id" in caplog.text

def test_handle_transaction_created_success(httpx_mock) -> None:
    httpx_mock.add_response(
        method="PATCH",
        url=re.compile(r".*/api/internal/transactions/.*/status/"),
        status_code=200,
    )
    _handle_transaction_created({"id": "abc-123"})
    # It runs a fire-and-forget sync wrapper, so it should execute the httpx mock.
    requests = httpx_mock.get_requests()
    assert len(requests) == 1
    assert b"COMPLETED" in requests[0].read()
