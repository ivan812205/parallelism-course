from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EventPaymentActivity(Base):
    """Агрегат покупок мероприятия по одному обработанному батчу."""

    __tablename__ = "event_payment_activity"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[UUID] = mapped_column(Uuid(), index=True)
    event_id: Mapped[int] = mapped_column(index=True)
    payments_count: Mapped[int]
    tickets_count: Mapped[int]
    total_amount: Mapped[int] = mapped_column(BigInteger())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
