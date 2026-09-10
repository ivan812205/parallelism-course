from app.tasks.protection import recalculate_protection


class ProtectionTaskScheduler:
    """Реализация порта дорасчёта страховки поверх taskiq: кладёт задачу в очередь
    обращений к внешним API."""

    async def schedule(self, booking_id: int) -> None:
        await recalculate_protection.kiq(booking_id)
