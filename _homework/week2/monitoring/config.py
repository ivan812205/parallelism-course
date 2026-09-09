from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    host: str = "127.0.0.1"
    # основной сервис занимает 8000
    port: int = 8001


class PostgresConfig(BaseModel):
    # база общая с «Афишей», но таблица у мониторинга своя;
    # подключение идёт через pgbouncer (порт 6432)
    url: str = "postgresql+psycopg://postgres:postgres@localhost:6432/postgres"
    # transaction-режим pgbouncer не переживает серверные подготовленные запросы
    prepare_threshold: int | None = None


class KafkaConfig(BaseModel):
    bootstrap_servers: str = "localhost:9094"
    purchases_topic: str = "tickets.purchased"
    group_id: str = "payments-monitoring"
    # до 10 сообщений в батче, но ждём наполнения не дольше 500 мс
    max_records: int = 10
    batch_timeout_ms: int = 500


class WebSocketConfig(BaseModel):
    # медленный клиент не должен задерживать рассылку остальным
    send_timeout_seconds: float = 2.0
    queue_maxsize: int = 1_000


class MonitoringSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_nested_delimiter="__",
        env_file=".env",
        extra="ignore",
    )

    app: AppConfig = Field(default_factory=AppConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    kafka: KafkaConfig = Field(default_factory=KafkaConfig)
    websocket: WebSocketConfig = Field(default_factory=WebSocketConfig)
