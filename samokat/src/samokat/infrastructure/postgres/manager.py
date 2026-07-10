from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from samokat.config import PostgresConfig
from samokat.infrastructure.postgres.repositories.cart_items import CartItemRepo
from samokat.infrastructure.postgres.repositories.darkstore_products import (
    DarkstoreProductRepo,
)
from samokat.infrastructure.postgres.repositories.orders import OrderRepo
from samokat.infrastructure.postgres.repositories.products import ProductRepo
from samokat.infrastructure.postgres.repositories.products_categories import (
    ProductCategoryRepo,
)
from samokat.infrastructure.postgres.repositories.refresh_tokens import RefreshTokenRepo
from samokat.infrastructure.postgres.repositories.user_adresses import UserAddressRepo
from samokat.infrastructure.postgres.repositories.users import UserRepo


class PostgresClient:
    def __init__(self, config: PostgresConfig) -> None:
        self._engine: AsyncEngine = create_async_engine(
            config.url,
            echo=config.echo,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_pre_ping=True,
        )

        self._session_maker = async_sessionmaker(
            bind=self._engine,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator["DatabaseManager"]:
        async with self._session_maker() as session:
            db = DatabaseManager(session)
            try:
                yield db
            except Exception:
                await db.rollback()
                raise

    async def close(self) -> None:
        await self._engine.dispose()


class DatabaseManager:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def commit(self) -> None:
        await self.session.commit()

    async def rollback(self) -> None:
        await self.session.rollback()

    @property
    def users(self) -> UserRepo:
        return UserRepo(self.session)

    @property
    def refresh_tokens(self) -> RefreshTokenRepo:
        return RefreshTokenRepo(self.session)

    @property
    def user_addresses(self) -> UserAddressRepo:
        return UserAddressRepo(self.session)

    @property
    def categories(self) -> ProductCategoryRepo:
        return ProductCategoryRepo(self.session)

    @property
    def products(self) -> ProductRepo:
        return ProductRepo(self.session)

    @property
    def darkstore_products(self) -> DarkstoreProductRepo:
        return DarkstoreProductRepo(self.session)

    @property
    def cart_items(self) -> CartItemRepo:
        return CartItemRepo(self.session)

    @property
    def orders(self) -> OrderRepo:
        return OrderRepo(self.session)
