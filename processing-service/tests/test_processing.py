import json
import re

import pytest
from fastapi.testclient import TestClient

from app.hmac_utils import generate_signature, verify_signature
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# HMAC utility tests
# ---------------------------------------------------------------------------


def test_generate_and_verify_signature() -> None:
    payload = "hello world"
    sig = generate_signature(payload)
    assert verify_signature(payload, sig) is True


def test_verify_signature_rejects_tampered_payload() -> None:
    sig = generate_signature("original")
    assert verify_signature("tampered", sig) is False


def test_verify_signature_rejects_wrong_signature() -> None:
    assert verify_signature("data", "deadbeef" * 8) is False


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
    return {"X-Signature": generate_signature(raw)}


def test_process_returns_401_with_no_signature() -> None:
    body = _make_process_body()
    resp = client.post("/api/process/", json=body)
    assert resp.status_code == 422  # missing required header


def test_process_returns_401_with_wrong_signature() -> None:
    body = _make_process_body()
    resp = client.post(
        "/api/process/",
        json=body,
        headers={"X-Signature": "badsig"},
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
    raw = json.dumps(body, separators=(",", ":"))
    headers = {"X-Signature": generate_signature(raw)}

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
    raw = json.dumps(body, separators=(",", ":"))
    headers = {"X-Signature": generate_signature(raw)}

    resp = client.post("/api/process/", json=body, headers=headers)
    assert resp.status_code == 502
    assert resp.json()["detail"] == "account_service_unavailable"
