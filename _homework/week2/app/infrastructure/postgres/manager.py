from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import PostgresConfig
from app.infrastructure.postgres.repositories.bookings import BookingRepo
from app.infrastructure.postgres.repositories.event_seats import EventSeatRepo
from app.infrastructure.postgres.repositories.event_views import EventViewRepo
from app.infrastructure.postgres.repositories.events import EventRepo
from app.infrastructure.postgres.repositories.locations import LocationRepo


class PostgresClient:
    """Владеет движком и фабрикой сессий (пул соединений на всё приложение)."""

    def __init__(self, config: PostgresConfig) -> None:
        self._engine = create_async_engine(
            config.url,
            pool_pre_ping=True,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout_seconds,
        )
        # expire_on_commit=False — атрибуты живут после commit (нужно при сборке ответа)
        self._session_maker = async_sessionmaker(self._engine, expire_on_commit=False)

    @asynccontextmanager
    async def session(self) -> AsyncIterator["DatabaseManager"]:
        async with self._session_maker() as session:
            try:
                yield DatabaseManager(session, self._session_maker)
            except Exception:
                await session.rollback()
                raise

    async def close(self) -> None:
        await self._engine.dispose()


class DatabaseManager:
    """Сессия одного запроса + доступ к репозиториям. `transaction()` открывает
    НЕЗАВИСИМУЮ сессию — для конкурентных запросов (одна async-сессия не выдержит
    параллельных операций)."""

    def __init__(self, session: AsyncSession, session_maker: async_sessionmaker) -> None:
        self.session = session
        self._session_maker = session_maker

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator["DatabaseManager"]:
        async with self._session_maker() as session:
            try:
                yield DatabaseManager(session, self._session_maker)
            except Exception:
                await session.rollback()
                raise

    async def commit(self) -> None:
        await self.session.commit()

    @property
    def events(self) -> EventRepo:
        return EventRepo(self.session)

    @property
    def locations(self) -> LocationRepo:
        return LocationRepo(self.session)

    @property
    def event_seats(self) -> EventSeatRepo:
        return EventSeatRepo(self.session)

    @property
    def bookings(self) -> BookingRepo:
        return BookingRepo(self.session)

    @property
    def event_views(self) -> EventViewRepo:
        return EventViewRepo(self.session)
