import logging
from datetime import datetime, timezone

from app.infrastructure.postgres.manager import DatabaseManager

logger = logging.getLogger(__name__)


class ExpiredBookingCleaner:
    """Возвращает в продажу места просроченных неоплаченных броней и удаляет сами брони."""

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def release_expired(self) -> int:
        expired_ids = await self._db.bookings.list_expired(datetime.now(timezone.utc))
        if not expired_ids:
            return 0

        # порядок важен: сначала снимаем ссылку мест на бронь, потом удаляем брони
        await self._db.event_seats.release(expired_ids)
        await self._db.bookings.delete(expired_ids)
        await self._db.commit()
        logger.info("Просроченные брони удалены, места освобождены: %s", expired_ids)
        return len(expired_ids)
