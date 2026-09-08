from redis.asyncio import Redis

from app.config import EventViewConfig


class EventViewDeduplicator:
    """Отсекает повторные просмотры мероприятия с одного IP: ключ живёт окно
    дедупликации, поэтому обновление страницы новый просмотр не создаёт."""

    KEY_TEMPLATE = "event_view:{event_id}:{client_ip}"

    def __init__(self, redis: Redis, config: EventViewConfig) -> None:
        self._redis = redis
        self._config = config

    async def try_register(self, event_id: int, client_ip: str) -> bool:
        """True — просмотр уникальный и его нужно учесть."""
        registered = await self._redis.set(
            self.KEY_TEMPLATE.format(event_id=event_id, client_ip=client_ip),
            "1",
            nx=True,
            ex=self._config.dedup_ttl_seconds,
        )
        return bool(registered)
