from collections.abc import AsyncIterator

from dishka import Provider, Scope, make_async_container, provide
from dishka.integrations.fastapi import FastapiProvider
from redis.asyncio import Redis

from app.config import (
    BookingConfig,
    EventCacheConfig,
    EventLockConfig,
    EventViewConfig,
    KafkaConfig,
    PaymentApiConfig,
    PostgresConfig,
    ProtectionApiConfig,
    ProtectionRetryConfig,
    PurchaseGeneratorConfig,
    RedisConfig,
    ReportConfig,
    Settings,
)
from app.infrastructure.api_connectors.payment import PaymentConnector
from app.infrastructure.api_connectors.protection import ProtectionConnector
from app.infrastructure.kafka.purchase_event_publisher import PurchaseEventPublisher
from app.infrastructure.postgres.manager import DatabaseManager, PostgresClient
from app.infrastructure.redis.event_cache import EventCache
from app.infrastructure.redis.event_view_deduplicator import EventViewDeduplicator
from app.infrastructure.redis.redis_lock import RedisLock
from app.services.catalog import CatalogService
from app.services.checkout import CheckoutService
from app.services.dashboard import DashboardService
from app.services.event_reader import EventReader
from app.services.event_report_builder import EventReportBuilder
from app.services.event_view_collector import EventViewCollector
from app.services.event_view_tracker import EventViewTracker
from app.services.expired_booking_cleaner import ExpiredBookingCleaner
from app.services.organizer import OrganizerService
from app.services.payment import PaymentService
from app.services.protection_recalculator import ProtectionRecalculator
from app.services.purchase_event_generator import PurchaseEventGenerator


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
    def get_payment_config(self, settings: Settings) -> PaymentApiConfig:
        return settings.payment

    @provide(scope=Scope.APP)
    def get_protection_config(self, settings: Settings) -> ProtectionApiConfig:
        return settings.protection

    @provide(scope=Scope.APP)
    def get_booking_config(self, settings: Settings) -> BookingConfig:
        return settings.booking

    @provide(scope=Scope.APP)
    def get_event_cache_config(self, settings: Settings) -> EventCacheConfig:
        return settings.event_cache

    @provide(scope=Scope.APP)
    def get_event_lock_config(self, settings: Settings) -> EventLockConfig:
        return settings.event_lock

    @provide(scope=Scope.APP)
    def get_event_view_config(self, settings: Settings) -> EventViewConfig:
        return settings.event_views

    @provide(scope=Scope.APP)
    def get_report_config(self, settings: Settings) -> ReportConfig:
        return settings.reports

    @provide(scope=Scope.APP)
    def get_protection_retry_config(self, settings: Settings) -> ProtectionRetryConfig:
        return settings.protection_retry

    @provide(scope=Scope.APP)
    def get_kafka_config(self, settings: Settings) -> KafkaConfig:
        return settings.kafka

    @provide(scope=Scope.APP)
    def get_purchase_generator_config(self, settings: Settings) -> PurchaseGeneratorConfig:
        return settings.purchase_generator


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


class RedisProvider(Provider):
    @provide(scope=Scope.APP)
    async def get_redis(self, config: RedisConfig) -> AsyncIterator[Redis]:
        redis = Redis.from_url(config.url, decode_responses=True)
        yield redis
        await redis.aclose()

    @provide(scope=Scope.APP)
    def get_event_cache(self, redis: Redis, config: EventCacheConfig) -> EventCache:
        return EventCache(redis=redis, config=config)

    @provide(scope=Scope.APP)
    def get_event_lock(self, redis: Redis, config: EventLockConfig) -> RedisLock:
        return RedisLock(redis=redis, config=config)

    @provide(scope=Scope.APP)
    def get_event_view_deduplicator(
        self, redis: Redis, config: EventViewConfig
    ) -> EventViewDeduplicator:
        return EventViewDeduplicator(redis=redis, config=config)


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
    @provide(scope=Scope.APP)
    def get_event_view_collector(
        self,
        postgres: PostgresClient,
        config: EventViewConfig,
    ) -> EventViewCollector:
        # живёт всё приложение: своя очередь и фоновый воркер, стартует в lifespan
        return EventViewCollector(postgres=postgres, config=config)

    @provide(scope=Scope.APP)
    def get_event_report_builder(self, config: ReportConfig) -> EventReportBuilder:
        return EventReportBuilder(config=config)

    @provide(scope=Scope.APP)
    def get_purchase_event_publisher(self, config: KafkaConfig) -> PurchaseEventPublisher:
        # продюсер Kafka на всё приложение, поднимается и гасится в lifespan
        return PurchaseEventPublisher(config=config)

    @provide(scope=Scope.APP)
    def get_purchase_event_generator(
        self,
        publisher: PurchaseEventPublisher,
        config: PurchaseGeneratorConfig,
    ) -> PurchaseEventGenerator:
        return PurchaseEventGenerator(publisher=publisher, config=config)

    @provide(scope=Scope.REQUEST)
    def get_expired_booking_cleaner(self, db: DatabaseManager) -> ExpiredBookingCleaner:
        return ExpiredBookingCleaner(db=db)

    @provide(scope=Scope.REQUEST)
    def get_protection_recalculator(
        self,
        db: DatabaseManager,
        protection: ProtectionConnector,
        config: ProtectionRetryConfig,
    ) -> ProtectionRecalculator:
        return ProtectionRecalculator(db=db, protection=protection, config=config)

    @provide(scope=Scope.REQUEST)
    def get_catalog_service(self, db: DatabaseManager) -> CatalogService:
        return CatalogService(db=db)

    @provide(scope=Scope.REQUEST)
    def get_event_reader(
        self,
        db: DatabaseManager,
        cache: EventCache,
        lock: RedisLock,
        config: EventLockConfig,
    ) -> EventReader:
        return EventReader(db=db, cache=cache, lock=lock, config=config)

    @provide(scope=Scope.REQUEST)
    def get_event_view_tracker(
        self,
        deduplicator: EventViewDeduplicator,
        collector: EventViewCollector,
    ) -> EventViewTracker:
        return EventViewTracker(deduplicator=deduplicator, collector=collector)

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
        RedisProvider(),
        ConnectorProvider(),
        ServiceProvider(),
        FastapiProvider(),
    )
