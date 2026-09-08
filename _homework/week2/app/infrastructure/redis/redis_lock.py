import asyncio
import uuid

from redis.asyncio import Redis

from app.config import EventLockConfig


class RedisLock:
    """Распределённая блокировка на Redis: взятие через SET NX PX, снятие —
    скриптом со сверкой токена, чтобы процесс не снял чужую блокировку после
    истечения своего TTL."""

    RELEASE_SCRIPT = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    end
    return 0
    """

    def __init__(self, redis: Redis, config: EventLockConfig) -> None:
        self._redis = redis
        self._config = config
        self._release_script = redis.register_script(self.RELEASE_SCRIPT)

    async def acquire(self, key: str) -> str | None:
        """Возвращает токен владельца блокировки или None, если её держит другой."""
        token = uuid.uuid4().hex
        acquired = await self._redis.set(
            key,
            token,
            nx=True,
            px=int(self._config.ttl_seconds * 1000),
        )
        return token if acquired else None

    async def release(self, key: str, token: str) -> None:
        await self._release_script(keys=[key], args=[token])

    async def wait_released(self, key: str, timeout: float) -> None:
        """Ждёт снятия блокировки, но не дольше timeout: дальше решает вызывающий."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while await self._redis.exists(key):
            if loop.time() >= deadline:
                return
            await asyncio.sleep(self._config.poll_interval_seconds)
