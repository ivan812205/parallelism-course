"""Точка входа воркеров: связывает брокеры с DI-контейнером и регистрирует задачи.

Запуск воркера очереди:
    uv run taskiq worker app.tasks.worker:reports_broker
    uv run taskiq worker app.tasks.worker:external_broker
    uv run taskiq worker app.tasks.worker:maintenance_broker
"""

from dishka.integrations.taskiq import setup_dishka

from app.config import Settings
from app.ioc import create_container
from app.tasks import bookings, protection, reports  # noqa: F401 — регистрация задач
from app.tasks.brokers import external_broker, maintenance_broker, reports_broker

container = create_container(Settings())

for broker in (reports_broker, external_broker, maintenance_broker):
    setup_dishka(container=container, broker=broker)
