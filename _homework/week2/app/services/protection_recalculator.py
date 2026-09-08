import asyncio
import logging

from app.config import ProtectionRetryConfig
from app.domain.enums import BookingStatus
from app.infrastructure.api_connectors.protection import ProtectionConnector
from app.infrastructure.postgres.manager import DatabaseManager

logger = logging.getLogger(__name__)


class ProtectionRecalculator:
    """Дорасчёт страховки после того, как API страховки не ответил в отведённое ручке
    время. Цена пишется только той брони, которая всё ещё ждёт оплаты."""

    def __init__(
        self,
        db: DatabaseManager,
        protection: ProtectionConnector,
        config: ProtectionRetryConfig,
    ) -> None:
        self._db = db
        self._protection = protection
        self._config = config

    async def recalculate(self, booking_id: int) -> bool:
        booking = await self._db.bookings.get(booking_id)
        if booking is None:
            logger.info("Бронь %s не найдена, дорасчёт страховки не нужен", booking_id)
            return False
        if booking.status is not BookingStatus.pending_payment:
            logger.info(
                "Бронь %s в статусе %s, дорасчёт страховки не нужен",
                booking_id,
                booking.status.value,
            )
            return False

        event = await self._db.events.get(booking.event_id)
        if event is None:
            logger.warning("Мероприятие брони %s исчезло, дорасчёт невозможен", booking_id)
            return False

        for attempt in range(1, self._config.attempts + 1):
            quote = await self._protection.calculate(
                booking_id,
                booking.amount,
                event.category,
                event.starts_at,
            )
            if quote is not None:
                # статус мог измениться, пока ходили в API: пишем только под условием
                if not await self._db.bookings.set_protection_price(booking_id, quote.price):
                    logger.info("Бронь %s изменила статус, цена страховки не записана", booking_id)
                    return False
                await self._db.commit()
                logger.info(
                    "Страховка брони %s дорасчитана с попытки %s: %s",
                    booking_id,
                    attempt,
                    quote.price,
                )
                return True

            if attempt < self._config.attempts:
                await asyncio.sleep(self._config.delay_seconds)

        logger.warning(
            "Страховка брони %s не получена за %s попыток", booking_id, self._config.attempts
        )
        return False
