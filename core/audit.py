"""Lightweight audit publisher.

Publishes JSON events to RabbitMQ when ``AUDIT_PUBLISH_ENABLED`` is true; in
tests / dev it falls back to a structured log entry.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from django.conf import settings

logger = logging.getLogger("gateway.audit")


def publish(event_type: str, payload: dict[str, Any]) -> None:
    body = {
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "gateway-ms",
        "data": payload,
    }

    if not getattr(settings, "AUDIT_PUBLISH_ENABLED", False):
        logger.info("AUDIT %s", json.dumps(body, default=str))
        return

    try:
        import pika

        params = pika.URLParameters(settings.RABBITMQ_URL)
        with pika.BlockingConnection(params) as conn:
            channel = conn.channel()
            channel.exchange_declare(
                exchange=settings.AUDIT_EVENT_EXCHANGE,
                exchange_type="topic",
                durable=True,
            )
            channel.basic_publish(
                exchange=settings.AUDIT_EVENT_EXCHANGE,
                routing_key=f"gateway.{event_type}",
                body=json.dumps(body, default=str).encode("utf-8"),
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit publish failed (%s) — falling back to log", exc)
        logger.info("AUDIT %s", json.dumps(body, default=str))
