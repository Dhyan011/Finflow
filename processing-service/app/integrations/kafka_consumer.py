import json
import logging
import os
import threading
from typing import Callable

from confluent_kafka import Consumer, KafkaError, KafkaException

logger = logging.getLogger(__name__)

KAFKA_BROKERS = os.environ.get("KAFKA_BROKERS", "localhost:9093")
KAFKA_GROUP_ID = os.environ.get("KAFKA_GROUP_ID", "processing-service")
TOPICS = ["transaction.created"]


def _make_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": KAFKA_BROKERS,
            "group.id": KAFKA_GROUP_ID,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )


def start_consumer(handler: Callable[[dict], None]) -> threading.Thread:
    """
    Start a background daemon thread that consumes Kafka messages
    from the ``transaction.created`` topic and calls ``handler``
    with each decoded JSON payload.
    """

    def _run() -> None:
        consumer = _make_consumer()
        consumer.subscribe(TOPICS)
        logger.info("kafka_consumer_started", extra={"topics": TOPICS})
        try:
            while True:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    raise KafkaException(msg.error())
                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                    handler(payload)
                except Exception as exc:
                    logger.error(
                        "kafka_message_processing_failed",
                        extra={"error": str(exc)},
                    )
        finally:
            consumer.close()

    thread = threading.Thread(target=_run, daemon=True, name="kafka-consumer")
    thread.start()
    return thread
