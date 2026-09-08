"""Планировщик регламентных задач.

Запуск:
    uv run taskiq scheduler app.tasks.scheduler:scheduler
"""

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from app.tasks.worker import maintenance_broker

# расписание берётся из label `schedule` у самих задач
scheduler = TaskiqScheduler(
    broker=maintenance_broker,
    sources=[LabelScheduleSource(maintenance_broker)],
)
