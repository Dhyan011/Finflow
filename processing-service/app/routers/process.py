import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel

from app.hmac_utils import verify_signature
from app.integrations.account_client import update_transaction_status

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/process", tags=["processing"])


class ProcessRequest(BaseModel):
    transaction_id: str
    amount: float
    currency: str
    direction: str  # CREDIT | DEBIT


class ProcessResponse(BaseModel):
    transaction_id: str
    result: str
    message: str


@router.post("/", response_model=ProcessResponse, status_code=status.HTTP_200_OK)
async def process_transaction(
    body: ProcessRequest,
    request: Request,
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    x_nonce: str = Header(..., alias="X-Nonce"),
) -> ProcessResponse:
    """
    HMAC-authenticated endpoint.
    Requires X-Signature, X-Timestamp, and X-Nonce headers.
    """
    raw_body = await request.body()
    if not verify_signature(raw_body.decode(), x_signature, x_timestamp, x_nonce):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid_signature",
        )

    logger.info(
        "processing_transaction",
        extra={"transaction_id": body.transaction_id, "direction": body.direction},
    )

    # Simple rule-based processing: always approve for now (Airflow would replace this)
    success = await update_transaction_status(
        transaction_id=body.transaction_id,
        new_status="COMPLETED",
        reference=f"PROC-{body.transaction_id[:8].upper()}",
    )

    if success:
        return ProcessResponse(
            transaction_id=body.transaction_id,
            result="approved",
            message="Transaction processed and marked COMPLETED.",
        )

    # Couldn't reach account-service — return 502
    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="account_service_unavailable",
    )
