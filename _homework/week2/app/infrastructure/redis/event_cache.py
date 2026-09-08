import random

from redis.asyncio import Redis

from app.application.dto import EventData
from app.config import EventCacheConfig


class EventCache:
    """Кэш мероприятия в Redis. TTL пишется с jitter, чтобы ключи популярных
    мероприятий не протухали одновременно и не роняли лавину запросов на базу."""

    KEY_TEMPLATE = "event:{event_id}"

    def __init__(self, redis: Redis, config: EventCacheConfig) -> None:
        self._redis = redis
        self._config = config

    async def get(self, event_id: int) -> EventData | None:
        raw = await self._redis.get(self.KEY_TEMPLATE.format(event_id=event_id))
        return EventData.model_validate_json(raw) if raw else None

    async def set(self, event_id: int, event: EventData) -> None:
        jitter = random.randint(0, self._config.ttl_jitter_seconds)
        await self._redis.set(
            self.KEY_TEMPLATE.format(event_id=event_id),
            event.model_dump_json(),
            ex=self._config.ttl_seconds + jitter,
        )
