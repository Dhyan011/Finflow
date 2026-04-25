import json
import logging
from typing import Any

from confluent_kafka import KafkaException, Producer
from django.conf import settings

logger = logging.getLogger(__name__)

_producer: Producer | None = None


def get_producer() -> Producer:
    global _producer
    if _producer is None:
        _producer = Producer({"bootstrap.servers": settings.KAFKA_BROKERS})
    return _producer


def publish_event(topic: str, payload: dict[str, Any]) -> None:
    try:
        producer = get_producer()
        producer.produce(topic, value=json.dumps(payload).encode("utf-8"))
        producer.poll(0)
    except KafkaException as exc:
        logger.error(
            "kafka_publish_failed",
            extra={"topic": topic, "error": str(exc)},
        )
    except Exception as exc:
        logger.error(
            "kafka_publish_failed",
            extra={"topic": topic, "error": str(exc)},
        )
