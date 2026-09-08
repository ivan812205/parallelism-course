from collections.abc import AsyncIterator

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider

from app.config import (
    BookingConfig,
    PaymentApiConfig,
    PostgresConfig,
    ProtectionApiConfig,
    Settings,
)
from app.infrastructure.api_connectors.payment import PaymentConnector
from app.infrastructure.api_connectors.protection import ProtectionConnector
from app.infrastructure.postgres.manager import DatabaseManager, PostgresClient
from app.services.catalog import CatalogService
from app.services.checkout import CheckoutService
from app.services.dashboard import DashboardService
from app.services.organizer import OrganizerService
from app.services.payment import PaymentService


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
    def get_payment_config(self, settings: Settings) -> PaymentApiConfig:
        return settings.payment

    @provide(scope=Scope.APP)
    def get_protection_config(self, settings: Settings) -> ProtectionApiConfig:
        return settings.protection

    @provide(scope=Scope.APP)
    def get_booking_config(self, settings: Settings) -> BookingConfig:
        return settings.booking


class PostgresProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_postgres(self, config: PostgresConfig) -> AsyncIterator[PostgresClient]:
        postgres = PostgresClient(config)
        yield postgres
        await postgres.close()

    @provide(scope=Scope.REQUEST)
    async def get_db(self, postgres: PostgresClient) -> AsyncIterator[DatabaseManager]:
        async with postgres.session() as db:
            yield db


class ConnectorProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_payment_connector(
        self, config: PaymentApiConfig
    ) -> AsyncIterator[PaymentConnector]:
        connector = PaymentConnector(
            base_url=config.base_url,
            timeout=config.timeout,
            retry_count=config.retry_count,
            rate_limit_requests=30,
            rate_limit_interval=1.0,
        )
        yield connector
        await connector.close_client()

    @provide(scope=Scope.APP)
    async def get_protection_connector(
        self, config: ProtectionApiConfig
    ) -> AsyncIterator[ProtectionConnector]:
        connector = ProtectionConnector(base_url=config.base_url, timeout=config.timeout)
        yield connector
        await connector.close_client()


class ServiceProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_catalog_service(self, db: DatabaseManager) -> CatalogService:
        return CatalogService(db=db)

    @provide(scope=Scope.REQUEST)
    def get_organizer_service(self, db: DatabaseManager) -> OrganizerService:
        return OrganizerService(db=db)

    @provide(scope=Scope.REQUEST)
    def get_checkout_service(
        self,
        db: DatabaseManager,
        payment: PaymentConnector,
        protection: ProtectionConnector,
        booking_config: BookingConfig,
    ) -> CheckoutService:
        return CheckoutService(
            db=db,
            payment=payment,
            protection=protection,
            config=booking_config,
        )

    @provide(scope=Scope.REQUEST)
    def get_dashboard_service(self, db: DatabaseManager) -> DashboardService:
        return DashboardService(db=db)

    @provide(scope=Scope.REQUEST)
    def get_payment_service(
        self,
        db: DatabaseManager,
        payment: PaymentConnector,
    ) -> PaymentService:
        return PaymentService(db=db, payment=payment)


def create_container(settings: Settings):
    return make_async_container(
        ConfigProvider(settings),
        PostgresProvider(),
        ConnectorProvider(),
        ServiceProvider(),
        FastapiProvider(),
    )
