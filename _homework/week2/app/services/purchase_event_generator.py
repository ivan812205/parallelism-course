import asyncio
import logging
import random
import uuid
from datetime import datetime, timezone

from app.application.dto import PurchaseEventData
from app.config import PurchaseGeneratorConfig
from app.infrastructure.kafka.purchase_event_publisher import PurchaseEventPublisher

logger = logging.getLogger(__name__)


class PurchaseEventGenerator:
    """Фоновый генератор тестовых покупок: пишет события `tickets.purchased`
    в Kafka пачками, чтобы консьюмер мониторинга получал по несколько сообщений
    за один раз. Мероприятия выбираются из узкого диапазона, поэтому покупки
    регулярно относятся к одному и тому же мероприятию."""

    TICKET_PRICE_RANGE = (1_000, 3_000)
    TICKETS_RANGE = (1, 4)

    def __init__(
        self,
        publisher: PurchaseEventPublisher,
        config: PurchaseGeneratorConfig,
    ) -> None:
        self._publisher = publisher
        self._config = config
        self._worker: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if not self._config.enabled:
            logger.info("Генератор покупок выключен")
            return
        self._worker = asyncio.create_task(self._generate(), name="purchase-event-generator")

    async def stop(self) -> None:
        if self._worker is None:
            return
        self._worker.cancel()
        await asyncio.gather(self._worker, return_exceptions=True)
        self._worker = None

    async def _generate(self) -> None:
        while True:
            for _ in range(self._config.burst_size):
                await self._publisher.publish(self._build_event())
            await asyncio.sleep(self._config.interval_seconds)

    def _build_event(self) -> PurchaseEventData:
        tickets_count = random.randint(*self.TICKETS_RANGE)
        ticket_price = random.randint(*self.TICKET_PRICE_RANGE)
        return PurchaseEventData(
            payment_id=uuid.uuid4().hex[:8],
            event_id=random.randint(1, self._config.max_event_id),
            tickets_count=tickets_count,
            total_amount=tickets_count * ticket_price,
            paid_at=datetime.now(timezone.utc),
        )
