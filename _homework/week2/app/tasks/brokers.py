from typing import Any

from taskiq_redis import ListQueueBroker

from app.config import Settings

_settings = Settings()

# Воркер taskiq слушает очередь блокирующим BRPOP без таймаута, а redis-py 8 по умолчанию
# ставит таймаут чтения 5 секунд и роняет воркер на пустой очереди — читаем без таймаута.
_CONNECTION_KWARGS: dict[str, Any] = {
    "socket_timeout": None,
    "socket_keepalive": True,
    "health_check_interval": 30,
}

# три очереди по типу работы: отчёты, обращения к внешним API, регламентные задачи.
# Так тяжёлая генерация PDF не задерживает дорасчёт страховки и наоборот.
reports_broker = ListQueueBroker(
    _settings.redis.url,
    queue_name=_settings.taskiq.reports_queue,
    **_CONNECTION_KWARGS,
)
external_broker = ListQueueBroker(
    _settings.redis.url,
    queue_name=_settings.taskiq.external_queue,
    **_CONNECTION_KWARGS,
)
maintenance_broker = ListQueueBroker(
    _settings.redis.url,
    queue_name=_settings.taskiq.maintenance_queue,
    **_CONNECTION_KWARGS,
)

# брокеры, в которые кладёт задачи веб-приложение (их поднимает lifespan)
API_BROKERS = (reports_broker, external_broker)
