from collections.abc import AsyncIterator

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from argon2 import PasswordHasher

from samokat.config import (
    ClickHouseConfig,
    ConnectorsConfig,
    PostgresConfig,
    RedisConfig,
    Settings,
    TokenConfig,
)
from samokat.infrastructure.api_connectors.external.addresses import (
    AddressConnector,
)
from samokat.infrastructure.api_connectors.internal.darkstore import (
    DarkstoreConnector,
)
from samokat.infrastructure.api_connectors.internal.delivery import DeliveryConnector
from samokat.infrastructure.clickhouse.manager import (
    ClickHouseManager,
    create_clickhouse_manager,
)
from samokat.infrastructure.postgres.manager import DatabaseManager, PostgresClient
from samokat.infrastructure.redis.darkstore_products import DarkstoreProductsCache
from samokat.infrastructure.redis.manager import RedisManager, create_redis_manager
from samokat.infrastructure.redis.product_card_cache import ProductCache
from samokat.security.password_hasher import PasswordHasherManager
from samokat.security.security_manager import SecurityManager
from samokat.security.token_processor import TokenProcessor
from samokat.services.addresses import AddressService
from samokat.services.auth import AuthService
from samokat.services.cart import CartService
from samokat.services.darkstore_sync import DarkstoreSyncService
from samokat.services.orders import OrderService
from samokat.services.product import ProductService
from samokat.services.users import UserService


class ConfigProvider(Provider):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def get_settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def get_postgres_config(self, settings: Settings) -> PostgresConfig:
        return settings.postgres

    @provide(scope=Scope.APP)
    def get_redis_config(self, settings: Settings) -> RedisConfig:
        return settings.redis

    @provide(scope=Scope.APP)
    def get_clickhouse_config(self, settings: Settings) -> ClickHouseConfig:
        return settings.clickhouse

    @provide(scope=Scope.APP)
    def get_token_config(self, settings: Settings) -> TokenConfig:
        return settings.token

    @provide(scope=Scope.APP)
    def get_connectors_config(self, settings: Settings) -> ConnectorsConfig:
        return settings.connectors


class PostgresProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_postgres(
        self,
        config: PostgresConfig,
    ) -> AsyncIterator[PostgresClient]:
        postgres = PostgresClient(config)

        yield postgres

        await postgres.close()

    @provide(scope=Scope.REQUEST)
    async def get_db(
        self,
        postgres: PostgresClient,
    ) -> AsyncIterator[DatabaseManager]:
        async with postgres.session() as db:
            yield db


class RedisProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_redis_manager(
        self,
        config: RedisConfig,
    ) -> AsyncIterator[RedisManager]:
        redis = create_redis_manager(config)

        yield redis

        await redis.close()


class ClickHouseProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_clickhouse_manager(
        self,
        config: ClickHouseConfig,
    ) -> AsyncIterator[ClickHouseManager]:
        clickhouse = await create_clickhouse_manager(config)

        yield clickhouse

        await clickhouse.close()


class ConnectorProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_address_connector(
        self,
        config: ConnectorsConfig,
    ) -> AsyncIterator[AddressConnector]:
        address_config = config.address
        connector = AddressConnector(
            base_url=address_config.base_url,
            client_id=address_config.client_id,
            client_secret=address_config.client_secret.get_secret_value(),
        )

        yield connector

        await connector.close_client()

    @provide(scope=Scope.APP)
    async def get_darkstore_connector(
        self,
        config: ConnectorsConfig,
    ) -> AsyncIterator[DarkstoreConnector]:
        darkstore_config = config.darkstore
        connector = DarkstoreConnector(
            base_url=darkstore_config.base_url,
            headers={
                "X-API-Key": darkstore_config.api_key.get_secret_value(),
            },
        )

        yield connector

        await connector.close_client()

    @provide(scope=Scope.APP)
    async def get_delivery_connector(
        self,
        config: ConnectorsConfig,
    ) -> AsyncIterator[DeliveryConnector]:
        delivery_config = config.delivery
        connector = DeliveryConnector(
            base_url=delivery_config.base_url,
            headers={
                "X-API-Key": delivery_config.api_key.get_secret_value(),
            },
        )

        yield connector

        await connector.close_client()


class CacheProvider(Provider):
    @provide(scope=Scope.APP)
    def get_product_cache(
        self,
        redis: RedisManager,
    ) -> ProductCache:
        return ProductCache(redis)

    @provide(scope=Scope.APP)
    def get_darkstore_products_cache(
        self,
        redis: RedisManager,
    ) -> DarkstoreProductsCache:
        return DarkstoreProductsCache(redis)


class SecurityProvider(Provider):
    @provide(scope=Scope.APP)
    def get_password_hasher(self) -> PasswordHasherManager:
        return PasswordHasherManager(PasswordHasher())

    @provide(scope=Scope.APP)
    def get_token_processor(self, config: TokenConfig) -> TokenProcessor:
        return TokenProcessor(config)

    @provide(scope=Scope.APP)
    def get_security_manager(
        self,
        password_hasher: PasswordHasherManager,
        token_processor: TokenProcessor,
    ) -> SecurityManager:
        return SecurityManager(
            password_hasher=password_hasher,
            token_processor=token_processor,
        )


class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_user_service(
        self,
        db: DatabaseManager,
        redis: RedisManager,
        security_manager: SecurityManager,
    ) -> UserService:
        return UserService(
            db=db,
            redis=redis,
            security=security_manager,
        )

    @provide(scope=Scope.REQUEST)
    def get_auth_service(
        self,
        db: DatabaseManager,
        security_manager: SecurityManager,
    ) -> AuthService:
        return AuthService(
            db=db,
            security=security_manager,
        )

    @provide(scope=Scope.REQUEST)
    def get_cart_service(
        self,
        db: DatabaseManager,
        clickhouse: ClickHouseManager,
    ) -> CartService:
        return CartService(
            db=db,
            clickhouse=clickhouse,
        )

    @provide(scope=Scope.REQUEST)
    def get_address_service(
        self,
        db: DatabaseManager,
        address_connector: AddressConnector,
        darkstore_connector: DarkstoreConnector,
    ) -> AddressService:
        return AddressService(
            db=db,
            address_connector=address_connector,
            darkstore_connector=darkstore_connector,
        )

    @provide(scope=Scope.REQUEST)
    def get_product_service(
        self,
        db: DatabaseManager,
        product_cache: ProductCache,
        darkstore_products_cache: DarkstoreProductsCache,
    ) -> ProductService:
        return ProductService(
            db=db,
            product_cache=product_cache,
            darkstore_products_cache=darkstore_products_cache,
        )

    @provide(scope=Scope.REQUEST)
    def get_order_service(
        self,
        db: DatabaseManager,
        darkstore_connector: DarkstoreConnector,
        delivery_connector: DeliveryConnector,
    ) -> OrderService:
        return OrderService(
            db=db,
            darkstore_connector=darkstore_connector,
            delivery_connector=delivery_connector,
        )

    @provide(scope=Scope.REQUEST)
    def get_darkstore_sync_service(
        self,
        db: DatabaseManager,
        darkstore_connector: DarkstoreConnector,
        darkstore_products_cache: DarkstoreProductsCache,
    ) -> DarkstoreSyncService:
        return DarkstoreSyncService(
            db=db,
            darkstore_connector=darkstore_connector,
            darkstore_products_cache=darkstore_products_cache,
        )


def create_container(settings: Settings):
    return make_async_container(
        ConfigProvider(settings),
        PostgresProvider(),
        RedisProvider(),
        ClickHouseProvider(),
        ConnectorProvider(),
        CacheProvider(),
        SecurityProvider(),
        ServiceProvider(),
        FastapiProvider(),
    )
