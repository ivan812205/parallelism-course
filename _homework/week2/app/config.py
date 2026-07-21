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


class RedisConfig(BaseModel):
    url: str = "redis://localhost:7379/0"


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
