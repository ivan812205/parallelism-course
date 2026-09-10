import logging

from aiokafka import AIOKafkaProducer

from app.application.dto import PurchaseEventData
from app.config import KafkaConfig

logger = logging.getLogger(__name__)


class PurchaseEventPublisher:
    """Публикует факты покупок в Kafka. linger_ms даёт продюсеру короткое время
    накопить сообщения и отправить их одним сетевым запросом."""

    def __init__(self, config: KafkaConfig) -> None:
        self._topic = config.purchases_topic
        self._producer = AIOKafkaProducer(
            bootstrap_servers=config.bootstrap_servers,
            linger_ms=config.linger_ms,
        )

    async def start(self) -> None:
        await self._producer.start()
        logger.info("Продюсер Kafka запущен, топик %s", self._topic)

    async def stop(self) -> None:
        await self._producer.stop()

    async def publish(self, event: PurchaseEventData) -> None:
        # ключ — мероприятие: покупки одного мероприятия попадают в один партишен
        await self._producer.send(
            self._topic,
            value=event.model_dump_json().encode(),
            key=str(event.event_id).encode(),
        )
