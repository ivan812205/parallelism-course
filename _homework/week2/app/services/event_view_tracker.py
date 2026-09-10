from app.infrastructure.redis.event_view_deduplicator import EventViewDeduplicator
from app.services.event_view_collector import EventViewCollector


class EventViewTracker:
    """Учитывает просмотр мероприятия: отсекает повторы с одного IP и отдаёт
    уникальный просмотр агрегатору."""

    def __init__(
        self,
        deduplicator: EventViewDeduplicator,
        collector: EventViewCollector,
    ) -> None:
        self._deduplicator = deduplicator
        self._collector = collector

    async def track(self, event_id: int, client_ip: str | None) -> None:
        if client_ip is None:
            return
        if await self._deduplicator.try_register(event_id, client_ip):
            self._collector.register(event_id)
