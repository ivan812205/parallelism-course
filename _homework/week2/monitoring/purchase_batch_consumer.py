import asyncio
import logging
from uuid import uuid4

from aiokafka import AIOKafkaConsumer, ConsumerRecord

from monitoring.config import KafkaConfig
from monitoring.dto import PaymentActivityData, PurchaseEventData
from monitoring.monitoring_database import MonitoringDatabase
from monitoring.purchase_aggregator import PurchaseAggregator

logger = logging.getLogger(__name__)


class PurchaseBatchConsumer:
    """Читает покупки из Kafka батчами, агрегирует их по мероприятиям, пишет
    одной транзакцией в PostgreSQL и только после этого коммитит offset.
    Сохранённые агрегаты уходят воркеру рассылки через asyncio.Queue."""

    def __init__(
        self,
        config: KafkaConfig,
        database: MonitoringDatabase,
        aggregator: PurchaseAggregator,
        queue: asyncio.Queue[list[PaymentActivityData] | None],
    ) -> None:
        self._config = config
        self._database = database
        self._aggregator = aggregator
        self._queue = queue
        # сам AIOKafkaConsumer создаётся в start(): ему нужен работающий событийный цикл
        self._consumer: AIOKafkaConsumer | None = None
        self._worker: asyncio.Task[None] | None = None

    async def start(self) -> None:
        self._consumer = AIOKafkaConsumer(
            self._config.purchases_topic,
            bootstrap_servers=self._config.bootstrap_servers,
            group_id=self._config.group_id,
            # подтверждаем сами — после успешной записи батча в базу
            enable_auto_commit=False,
            auto_offset_reset="earliest",
        )
        await self._consumer.start()
        self._worker = asyncio.create_task(
            self._consume(self._consumer), name="purchase-batch-consumer"
        )
        logger.info(
            "Консьюмер запущен: топик %s, батч до %s сообщений, ожидание до %s мс",
            self._config.purchases_topic,
            self._config.max_records,
            self._config.batch_timeout_ms,
        )

    async def stop(self) -> None:
        if self._worker is not None:
            self._worker.cancel()
            await asyncio.gather(self._worker, return_exceptions=True)
            self._worker = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def _consume(self, consumer: AIOKafkaConsumer) -> None:
        while True:
            batches = await consumer.getmany(
                timeout_ms=self._config.batch_timeout_ms,
                max_records=self._config.max_records,
            )
            records = [record for partition in batches.values() for record in partition]
            if not records:
                continue
            try:
                await self._handle_batch(consumer, records)
            except Exception:
                # offset не подтверждён: откатываемся к подтверждённой позиции,
                # брокер отдаст эти сообщения снова
                logger.exception("Батч из %s сообщений не обработан", len(records))
                await consumer.seek_to_committed()

    async def _handle_batch(
        self,
        consumer: AIOKafkaConsumer,
        records: list[ConsumerRecord],
    ) -> None:
        events = [PurchaseEventData.model_validate_json(record.value) for record in records]
        aggregates = self._aggregator.aggregate(events)
        batch_id = uuid4()

        await self._database.save_activity(batch_id=batch_id, aggregates=aggregates)
        await consumer.commit()
        logger.info(
            "Батч %s: сообщений %s, мероприятий %s — записан в базу, offset подтверждён",
            batch_id,
            len(records),
            len(aggregates),
        )

        # рассылка не влияет на подтверждение: агрегаты уже в базе
        try:
            self._queue.put_nowait(aggregates)
        except asyncio.QueueFull:
            logger.warning("Очередь рассылки переполнена, батч %s не уйдёт клиентам", batch_id)
