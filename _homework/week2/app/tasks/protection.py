from dishka.integrations.taskiq import FromDishka, inject

from app.services.protection_recalculator import ProtectionRecalculator
from app.tasks.brokers import external_broker


@external_broker.task(task_name="protection.recalculate")
@inject
async def recalculate_protection(
    booking_id: int,
    recalculator: FromDishka[ProtectionRecalculator],
) -> bool:
    """Дорасчёт страховки для брони, которой не хватило времени в ручке оформления."""
    return await recalculator.recalculate(booking_id)
