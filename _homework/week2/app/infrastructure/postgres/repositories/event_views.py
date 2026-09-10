from sqlalchemy.dialects.postgresql import insert

from app.infrastructure.postgres.models import EventView
from app.infrastructure.postgres.repositories.base import BaseRepo


class EventViewRepo(BaseRepo):
    async def increment(self, views_by_event: dict[int, int]) -> None:
        """Прибавляет накопленные просмотры одним запросом: строка на мероприятие,
        а не на просмотр."""
        statement = insert(EventView).values(
            [
                {"event_id": event_id, "views_count": views_count}
                for event_id, views_count in views_by_event.items()
            ]
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[EventView.event_id],
                set_={"views_count": EventView.views_count + statement.excluded.views_count},
            )
        )
