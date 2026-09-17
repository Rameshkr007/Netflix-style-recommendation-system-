"""
WebSocket endpoint backed by Redis Pub/Sub.

Supports multiple API instances behind a load balancer:
- Each client connects to /ws/live?channel=trending (or system, etc.)
- Redis Pub/Sub fans out messages to ALL instances' local clients
- If Redis is down, falls back to local-only broadcast gracefully

Channels:
  trending  →  real-time trending content updates
  system    →  model refresh alerts, maintenance notices
"""
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.pubsub import CHANNEL_SYSTEM, CHANNEL_TRENDING, pubsub_manager

router = APIRouter(tags=["WebSocket"])

CHANNEL_MAP = {
    "trending": CHANNEL_TRENDING,
    "system":   CHANNEL_SYSTEM,
}


@router.websocket("/ws/live")
async def websocket_endpoint(
    websocket: WebSocket,
    channel: str = "trending",
):
    """
    Connect to a real-time broadcast channel.

    Query params:
      channel: 'trending' | 'system'  (default: trending)

    Message types received:
      { type: 'trending_update', titles: [...] }
      { type: 'system_alert', message: '...', level: 'info'|'warning' }
      { type: 'pong' }  (response to client ping)
    """
    redis_channel = CHANNEL_MAP.get(channel, CHANNEL_TRENDING)
    await pubsub_manager.connect(websocket, redis_channel)

    try:
        # Send a welcome message with current connection count
        await websocket.send_json({
            "type": "connected",
            "channel": channel,
            "active_connections": pubsub_manager.total_local_connections,
        })

        # Keep-alive loop: accept pings, ignore other messages
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {}

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        pubsub_manager.disconnect(websocket, redis_channel)


# ── Convenience functions for internal use ────────────────────────────────

async def notify_trending_update(titles: list[str]) -> None:
    """Call from admin/trending job after recomputing trending list."""
    await pubsub_manager.broadcast_trending(titles)


async def notify_model_refreshed() -> None:
    """Call after /admin/model/refresh completes."""
    await pubsub_manager.broadcast_system_alert(
        "Recommendation model refreshed — personalized picks updated!",
        level="info",
    )
