import asyncio
import logging

from app.application.dto import EventData
from app.config import EventLockConfig
from app.domain.exceptions import EventNotFoundError, EventUnavailableError
from app.infrastructure.postgres.manager import DatabaseManager
from app.infrastructure.redis.event_cache import EventCache
from app.infrastructure.redis.redis_lock import RedisLock

logger = logging.getLogger(__name__)


class EventReader:
    """Чтение мероприятия под нагрузкой: кэш Redis плюс распределённый SingleFlight,
    поэтому при пустом кэше в PostgreSQL уходит один запрос, а остальные процессы
    ждут результата и читают его из кэша."""

    LOCK_KEY_TEMPLATE = "lock:event:{event_id}"

    def __init__(
        self,
        db: DatabaseManager,
        cache: EventCache,
        lock: RedisLock,
        config: EventLockConfig,
    ) -> None:
        self._db = db
        self._cache = cache
        self._lock = lock
        self._config = config

    async def get_event(self, event_id: int) -> EventData:
        cached = await self._cache.get(event_id)
        if cached is not None:
            return cached

        lock_key = self.LOCK_KEY_TEMPLATE.format(event_id=event_id)
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._config.wait_timeout_seconds
        while True:
            token = await self._lock.acquire(lock_key)
            if token is not None:
                try:
                    return await self._load_event(event_id)
                finally:
                    await self._lock.release(lock_key, token)

            await self._lock.wait_released(lock_key, timeout=max(deadline - loop.time(), 0.0))
            cached = await self._cache.get(event_id)
            if cached is not None:
                return cached
            if loop.time() >= deadline:
                raise EventUnavailableError

    async def _load_event(self, event_id: int) -> EventData:
        # повторная проверка под блокировкой: пока ждали её, данные мог положить сосед
        cached = await self._cache.get(event_id)
        if cached is not None:
            return cached

        event = await self._db.events.get(event_id)
        if event is None:
            raise EventNotFoundError
        await self._cache.set(event_id, event)
        logger.info("Мероприятие %s загружено из PostgreSQL", event_id)
        return event
