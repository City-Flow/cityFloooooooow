# cityFlow/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class AlertConsumer(AsyncWebsocketConsumer):
    """WebSocket que emite alertas en vivo al dashboard."""

    async def connect(self):
        self.user = self.scope["user"]

        # ⚠️ Para test rápido dejamos pasar sin auth.
        # Cuando implementes login, descomenta esto:
        # if not self.user.is_authenticated:
        #     await self.close(code=4401)
        #     return

        self.groups_joined = ["alerts"]
        for g in self.groups_joined:
            await self.channel_layer.group_add(g, self.channel_name)

        await self.accept()

        await self.send(text_data=json.dumps({
            "type": "connection.established",
            "user": str(self.user) if self.user.is_authenticated else "anonymous",
        }))

    async def disconnect(self, close_code):
        for g in getattr(self, "groups_joined", []):
            await self.channel_layer.group_discard(g, self.channel_name)

    async def alert_message(self, event):
        """Envía al navegador el payload de la alerta."""
        await self.send(text_data=json.dumps(event["payload"]))