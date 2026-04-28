import logging
import os

import httpx

logger = logging.getLogger(__name__)

ACCOUNT_SERVICE_URL = os.environ.get(
    "ACCOUNT_SERVICE_URL", "http://localhost:8000"
)

# Shared HMAC secret — must match account-service value
INTERNAL_SECRET = os.environ.get("INTERNAL_SECRET", "dev-internal-secret")


async def update_transaction_status(
    transaction_id: str,
    new_status: str,
    reference: str = "",
) -> bool:
    """
    Call account-service internal endpoint to update transaction status.
    Returns True on success, False on any error.
    """
    url = f"{ACCOUNT_SERVICE_URL}/api/internal/transactions/{transaction_id}/status/"
    payload = {"status": new_status, "reference": reference}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(url, json=payload)
            resp.raise_for_status()
            logger.info(
                "transaction_status_updated",
                extra={"transaction_id": transaction_id, "status": new_status},
            )
            return True
    except httpx.HTTPStatusError as exc:
        logger.error(
            "account_service_error",
            extra={
                "transaction_id": transaction_id,
                "status_code": exc.response.status_code,
            },
        )
    except Exception as exc:
        logger.error(
            "account_service_unreachable",
            extra={"transaction_id": transaction_id, "error": str(exc)},
        )
    return False
