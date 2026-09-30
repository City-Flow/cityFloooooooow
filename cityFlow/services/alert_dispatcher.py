# cityFlow/services/alert_dispatcher.py
"""Punto único para crear Alert + notificar por WebSocket (Fase 4)."""

from __future__ import annotations

import logging

from cityFlow.models import Alert, District

logger = logging.getLogger(__name__)


def create_alert(
    *,
    district: District,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    related_object_id: int | None = None,
) -> Alert:
    """Crea una Alert persistente. (El broadcast WS se añade en la Fase 4)."""
    alert = Alert.objects.create(
        district=district,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        related_object_id=related_object_id,
    )
    logger.info("Alert creada: [%s] %s (district=%s)", severity, title, district.code)
    return alert