import asyncio
from dataclasses import dataclass

from job_status import JobStatus


@dataclass
class Job:
    status: JobStatus
    result: dict | None = None
    error: str | None = None
    task: asyncio.Task | None = None  # ссылка на фоновую задачу, чтобы её не собрал GC


# Хранилище джоб в памяти приложения: job_id -> Job
jobs: dict[str, Job] = {}
