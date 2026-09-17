"""
Redis Pub/Sub WebSocket Manager
---------------------------------
Production-grade WebSocket broadcasting that works across multiple
API instances behind a load balancer.

Problem with naive in-process ConnectionManager:
  - Instance A has users X, Y connected
  - Instance B has users Z, W connected
  - If trending updates on Instance A → only X, Y get the update
  - Z, W on Instance B never receive it

Solution: Redis Pub/Sub
  - Any instance that has new data PUBLISHES to a Redis channel
  - ALL instances are SUBSCRIBED to that channel
  - Each instance fans out to its locally connected WebSocket clients
  - Result: all clients on all instances get every broadcast

Channel structure:
  aperture:broadcast:trending   → trending content updates
  aperture:broadcast:system     → system-wide alerts
  aperture:broadcast:user:{id}  → user-specific notifications
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import TYPE_CHECKING

import redis.asyncio as aioredis

from app.core.config import get_settings

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger(__name__)
settings = get_settings()

# Channel name constants
CHANNEL_TRENDING = "aperture:broadcast:trending"
CHANNEL_SYSTEM   = "aperture:broadcast:system"


class RedisPubSubManager:
    """
    Manages Redis Pub/Sub for broadcasting WebSocket messages across
    multiple API instances. Each instance holds its own set of active
    WebSocket connections and uses Redis as a message bus.
    """

    def __init__(self):
        self._local_connections: dict[str, set["WebSocket"]] = {}
        self._redis_client: aioredis.Redis | None = None
        self._pubsub: aioredis.client.PubSub | None = None
        self._listener_task: asyncio.Task | None = None
        self._subscribed_channels: set[str] = set()

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis_client is None:
            self._redis_client = await aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_keepalive=True,
            )
        return self._redis_client

    # ── Connection management (local to this instance) ─────────────────────

    async def connect(self, websocket: "WebSocket", channel: str) -> None:
        """Accept a WebSocket and register it to a channel."""
        await websocket.accept()
        if channel not in self._local_connections:
            self._local_connections[channel] = set()
            await self._subscribe_channel(channel)
        self._local_connections[channel].add(websocket)
        logger.debug("WS connected on channel=%s total=%d",
                     channel, len(self._local_connections[channel]))

    def disconnect(self, websocket: "WebSocket", channel: str) -> None:
        """Remove a WebSocket from local registry."""
        conns = self._local_connections.get(channel, set())
        conns.discard(websocket)
        logger.debug("WS disconnected from channel=%s remaining=%d", channel, len(conns))

    async def _local_broadcast(self, channel: str, message: dict) -> None:
        """Send a message to all locally connected clients on a channel."""
        conns = list(self._local_connections.get(channel, set()))
        dead = []
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)

    # ── Redis Pub/Sub ──────────────────────────────────────────────────────

    async def _subscribe_channel(self, channel: str) -> None:
        """Subscribe this instance to a Redis channel."""
        if channel in self._subscribed_channels:
            return
        try:
            redis = await self._get_redis()
            if self._pubsub is None:
                self._pubsub = redis.pubsub()
            await self._pubsub.subscribe(channel)
            self._subscribed_channels.add(channel)
            if self._listener_task is None or self._listener_task.done():
                self._listener_task = asyncio.create_task(self._redis_listener())
            logger.info("Subscribed to Redis channel: %s", channel)
        except Exception as e:
            logger.warning("Redis subscribe failed (falling back to local-only): %s", e)

    async def _redis_listener(self) -> None:
        """
        Background task: listen for Redis messages and fan out to
        local WebSocket clients. Runs for the lifetime of the process.
        """
        logger.info("Redis Pub/Sub listener started")
        try:
            async for message in self._pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    channel = message["channel"]
                    await self._local_broadcast(channel, data)
                except (json.JSONDecodeError, Exception) as e:
                    logger.warning("Failed to process pubsub message: %s", e)
        except asyncio.CancelledError:
            logger.info("Redis Pub/Sub listener cancelled")
        except Exception as e:
            logger.error("Redis Pub/Sub listener error: %s", e)

    async def publish(self, channel: str, message: dict) -> None:
        """
        Publish a message to ALL instances via Redis.
        Falls back to local-only broadcast if Redis is unavailable.
        """
        payload = json.dumps(message)
        try:
            redis = await self._get_redis()
            subscribers = await redis.publish(channel, payload)
            logger.debug("Published to %s: %d subscribers", channel, subscribers)
        except Exception as e:
            logger.warning("Redis publish failed, falling back to local broadcast: %s", e)
            await self._local_broadcast(channel, message)

    # ── High-level broadcast methods ───────────────────────────────────────

    async def broadcast_trending(self, titles: list[str]) -> None:
        """Broadcast updated trending titles to all connected clients."""
        await self.publish(CHANNEL_TRENDING, {
            "type": "trending_update",
            "titles": titles,
        })

    async def broadcast_system_alert(self, message: str, level: str = "info") -> None:
        """Broadcast a system-wide alert (model refresh, maintenance, etc.)."""
        await self.publish(CHANNEL_SYSTEM, {
            "type": "system_alert",
            "message": message,
            "level": level,
        })

    @property
    def total_local_connections(self) -> int:
        return sum(len(conns) for conns in self._local_connections.values())

    async def cleanup(self) -> None:
        """Graceful shutdown: cancel listener, close Redis connection."""
        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.aclose()
        if self._redis_client:
            await self._redis_client.aclose()
        logger.info("RedisPubSubManager cleaned up")


# Singleton instance — one per API process
pubsub_manager = RedisPubSubManager()
