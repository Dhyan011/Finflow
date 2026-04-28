import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.integrations.account_client import update_transaction_status
from app.integrations.kafka_consumer import start_consumer
from app.routers import process

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start Kafka consumer on startup; nothing special on shutdown."""
    try:
        start_consumer(_handle_transaction_created)
        logger.info("kafka_consumer_started_successfully")
    except Exception as exc:  # pragma: no cover
        logger.warning(
            "kafka_consumer_start_failed",
            extra={"error": str(exc)},
        )
    yield


app = FastAPI(
    title="FinFlow Processing Service",
    version="1.0.0",
    description="Async transaction processing microservice with Kafka consumption.",
    lifespan=lifespan,
)

app.include_router(process.router)


def _handle_transaction_created(payload: dict) -> None:
    """
    Kafka message handler for ``transaction.created`` events.
    Schedules an async status update back to account-service.
    """
    transaction_id = payload.get("id")
    logger.info(
        "kafka_event_received",
        extra={"transaction_id": transaction_id, "topic": "transaction.created"},
    )
    if not transaction_id:
        logger.warning("kafka_event_missing_id", extra={"payload": payload})
        return

    # Fire-and-forget async task using asyncio event loop
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(
            update_transaction_status(
                transaction_id=transaction_id,
                new_status="COMPLETED",
                reference=f"KAFKA-{transaction_id[:8].upper()}",
            )
        )
    finally:
        loop.close()


@app.get("/health", tags=["ops"])
async def health() -> dict:
    return {"status": "ok", "service": "processing-service"}
