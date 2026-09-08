from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = True
    # урок 9: верхний предел на всю бизнес-операцию (< серверного таймаута)
    request_timeout: float = 10.0


class PostgresConfig(BaseModel):
    url: str = "postgresql+psycopg://postgres:postgres@localhost:7432/postgres"
    # Пул по умолчанию (5 + 10) упирается уже на десятках конкурентных запросов:
    # дашборд берёт две независимые сессии, и запросы встают в очередь.
    # Считать надо на все процессы: воркеры × (pool_size + max_overflow) должно быть
    # меньше max_connections PostgreSQL (по умолчанию 100). Проверено в ДЗ 6:
    # 4 воркера × (20 + 20) дают «FATAL: sorry, too many clients already».
    pool_size: int = 10
    max_overflow: int = 10
    # ждать соединение полминуты бессмысленно: клиент уже ушёл
    pool_timeout_seconds: float = 5.0


class RedisConfig(BaseModel):
    url: str = "redis://localhost:7379/0"
    # при исчерпании пула ждём соединение, а не падаем с MaxConnectionsError
    max_connections: int = 256
    pool_timeout_seconds: float = 3.0


class PaymentApiConfig(BaseModel):
    base_url: str = "http://localhost:9001"
    timeout: float = 5.0
    # платёж критичен: ретраим 429 несколько раз (мок отдаёт 429 на каждый 6-й)
    retry_count: int = 5


class ProtectionApiConfig(BaseModel):
    base_url: str = "http://localhost:9002"
    # страховка некритична: жёсткий бюджет ожидания, без ретраев
    timeout: float = 3.0


class BookingConfig(BaseModel):
    ttl_minutes: int = 15


class EventCacheConfig(BaseModel):
    ttl_seconds: int = 60
    # jitter: разброс TTL, чтобы ключи популярных мероприятий не протухали разом
    ttl_jitter_seconds: int = 15


class EventLockConfig(BaseModel):
    # блокировку держит только загрузчик, TTL страхует от упавшего процесса
    ttl_seconds: float = 5.0
    # бюджет ожидания для тех, кто блокировку не получил
    wait_timeout_seconds: float = 3.0
    poll_interval_seconds: float = 0.05


class EventViewConfig(BaseModel):
    # просмотр мероприятия с одного IP считается не чаще раза в 5 минут
    dedup_ttl_seconds: int = 300
    # сброс агрегатов в базу: по числу просмотров либо по таймеру
    flush_every_events: int = 10
    flush_interval_seconds: float = 5.0
    queue_maxsize: int = 10_000


class TaskiqConfig(BaseModel):
    # свои очереди на каждый тип фоновых задач: отчёты, внешние API, регламентные работы
    reports_queue: str = "afisha.reports"
    external_queue: str = "afisha.external"
    maintenance_queue: str = "afisha.maintenance"


class ReportConfig(BaseModel):
    # на проде тут было бы S3, локально — каталог рядом с приложением
    directory: str = "reports"


class ProtectionRetryConfig(BaseModel):
    # ручка ждала страховку не дольше своего таймаута, фон пробует ещё дважды
    attempts: int = 2
    delay_seconds: float = 2.0


class KafkaConfig(BaseModel):
    bootstrap_servers: str = "localhost:9094"
    purchases_topic: str = "tickets.purchased"
    # продюсер копит сообщения этот интервал и отправляет их одним запросом
    linger_ms: int = 75


class PurchaseGeneratorConfig(BaseModel):
    enabled: bool = True
    # поток подобран так, чтобы консьюмер регулярно набирал полный батч (10 сообщений)
    # и при затишье срабатывал по таймауту 500 мс
    interval_seconds: float = 0.2
    burst_size: int = 8
    # узкий диапазон мероприятий: покупки регулярно попадают на одно и то же
    max_event_id: int = 5


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    app: AppConfig = Field(default_factory=AppConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    payment: PaymentApiConfig = Field(default_factory=PaymentApiConfig)
    protection: ProtectionApiConfig = Field(default_factory=ProtectionApiConfig)
    booking: BookingConfig = Field(default_factory=BookingConfig)
    event_cache: EventCacheConfig = Field(default_factory=EventCacheConfig)
    event_lock: EventLockConfig = Field(default_factory=EventLockConfig)
    event_views: EventViewConfig = Field(default_factory=EventViewConfig)
    taskiq: TaskiqConfig = Field(default_factory=TaskiqConfig)
    reports: ReportConfig = Field(default_factory=ReportConfig)
    protection_retry: ProtectionRetryConfig = Field(default_factory=ProtectionRetryConfig)
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    purchase_generator: PurchaseGeneratorConfig = Field(
        default_factory=PurchaseGeneratorConfig
    )
