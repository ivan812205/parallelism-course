from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from monitoring.config import PostgresConfig
from monitoring.dto import PaymentActivityData
from monitoring.models import EventPaymentActivity


class MonitoringDatabase:
    """Хранилище агрегатов активности оплат."""

    def __init__(self, config: PostgresConfig) -> None:
        self._engine = create_async_engine(
            config.url,
            pool_pre_ping=True,
            connect_args={"prepare_threshold": config.prepare_threshold},
        )
        self._session_maker = async_sessionmaker(self._engine, expire_on_commit=False)

    async def save_activity(
        self,
        *,
        batch_id: UUID,
        aggregates: list[PaymentActivityData],
    ) -> None:
        """Все агрегаты батча пишутся одной транзакцией: либо батч целиком в базе,
        либо в базе нет ничего и сообщения не подтверждаются брокеру."""
        async with self._session_maker() as session, session.begin():
            session.add_all(
                EventPaymentActivity(
                    batch_id=batch_id,
                    event_id=aggregate.event_id,
                    payments_count=aggregate.payments_count,
                    tickets_count=aggregate.tickets_count,
                    total_amount=aggregate.total_amount,
                )
                for aggregate in aggregates
            )

    async def close(self) -> None:
        await self._engine.dispose()
