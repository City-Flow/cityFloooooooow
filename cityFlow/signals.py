# cityFlow/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Alert


@receiver(post_save, sender=Alert)
def broadcast_alert(sender, instance: Alert, created, **kwargs):
    """Cuando se crea una Alert, la empuja al grupo WebSocket."""
    if not created:
        return

    channel_layer = get_channel_layer()
    payload = {
        "type": "water_anomaly.created" if instance.alert_type == "water_anomaly"
                else f"{instance.alert_type}.created",
        "alert_id": instance.id,
        "district_id": instance.district_id,
        "district_name": instance.district.name,
        "severity": instance.severity,
        "title": instance.title,
        "message": instance.message,
        "created_at": instance.created_at.isoformat(),
    }

    async_to_sync(channel_layer.group_send)(
        "alerts",
        {"type": "alert.message", "payload": payload},
    )