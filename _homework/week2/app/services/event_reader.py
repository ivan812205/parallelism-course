import asyncio
import logging

from redis.asyncio import Redis

from app.application.dto import EventData
from app.config import EventLockConfig
from app.domain.exceptions import EventNotFoundError, EventUnavailableError
from app.infrastructure.postgres.manager import DatabaseManager
from app.infrastructure.redis.event_cache import EventCache

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
        redis: Redis,
        config: EventLockConfig,
    ) -> None:
        self._db = db
        self._cache = cache
        self._redis = redis
        self._config = config

    async def get_event(self, event_id: int) -> EventData:
        cached = await self._cache.get(event_id)
        if cached is not None:
            return cached

        # Lock из redis-py: сам кладёт SET NX PX со своим токеном и снимает блокировку
        # Lua-скриптом со сверкой токена, поэтому чужую блокировку снять нельзя.
        # raise_on_release_error=False — если TTL истёк, снимать уже нечего.
        lock = self._redis.lock(
            self.LOCK_KEY_TEMPLATE.format(event_id=event_id),
            timeout=self._config.ttl_seconds,
            thread_local=False,
            raise_on_release_error=False,
        )
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self._config.wait_timeout_seconds
        while True:
            # неблокирующее взятие: ждать блокировку внутри Lock не даём — проигравшие
            # смотрят на кэш, а не на замок, и уходят сразу, как только он наполнен
            if await lock.acquire(blocking=False):
                try:
                    return await self._load_event(event_id)
                finally:
                    await lock.release()

            cached = await self._cache.get(event_id)
            if cached is not None:
                return cached
            if loop.time() >= deadline:
                raise EventUnavailableError
            await asyncio.sleep(self._config.poll_interval_seconds)

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
