from datetime import datetime

from pydantic import BaseModel, ConfigDict

_FROZEN = ConfigDict(frozen=True)


class PurchaseEventData(BaseModel):
    """Событие `tickets.purchased` в том виде, в котором его публикует «Афиша»."""

    model_config = _FROZEN

    payment_id: str
    event_id: int
    tickets_count: int
    total_amount: int
    paid_at: datetime


class PaymentActivityData(BaseModel):
    """Агрегат покупок одного мероприятия внутри одного батча."""

    model_config = _FROZEN

    event_id: int
    payments_count: int
    tickets_count: int
    total_amount: int
