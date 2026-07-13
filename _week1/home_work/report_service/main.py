import asyncio
import uuid

import httpx
from fastapi import FastAPI, HTTPException

from job_status import JobStatus
from legacy_client import get_user_todos_sync
from store import Job, jobs

app = FastAPI()


# 1. запуск задачи: сразу отдаём job_id, отчёт считаем в фоне
@app.post("/reports/{user_id}")
async def create_report(user_id: int):
    job_id = str(uuid.uuid4())
    job = jobs[job_id] = Job(status=JobStatus.RUNNING)

    # ссылку на задачу держим в самой джобе — она жива, пока джоба лежит в jobs
    job.task = asyncio.create_task(build_report(job_id, user_id))

    return {"job_id": job_id, "status": JobStatus.RUNNING}


# 2. статус задачи: running / error / done (+ result)
@app.get("/reports/jobs/{job_id}")
async def get_report(job_id: str):
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")
    response = {"job_id": job_id, "status": job.status}
    if job.status == JobStatus.DONE:
        response["result"] = job.result
    elif job.status == JobStatus.ERROR:
        response["error"] = job.error
    return response


# 5. проверка, что приложение не блокируется
@app.get("/ping")
async def ping():
    return {"status": "ok"}


async def fetch_user(user_id: int) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"https://dummyjson.com/users/{user_id}")
    return resp.json()


# 3. сбор отчёта в фоне
async def build_report(job_id: str, user_id: int) -> None:
    job = jobs[job_id]
    try:
        # юзер (async, в loop) и todos (легаси, в отдельном потоке) — параллельно
        user, todos_data = await asyncio.gather(
            fetch_user(user_id),
            asyncio.to_thread(get_user_todos_sync, user_id),
        )
        todos = todos_data["todos"]

        job.result = {
            "user": {
                "user_id": user["id"],
                "user_name": user["firstName"],
                "email": user["email"],
            },
            "todos": {
                "total": len(todos),
                "completed": sum(1 for t in todos if t["completed"]),
                "items": [
                    {"id": t["id"], "todo": t["todo"], "completed": t["completed"]}
                    for t in todos
                ],
            },
        }
        job.status = JobStatus.DONE
    except Exception as exc:  # любой сбой → сохраняем и помечаем error
        job.status = JobStatus.ERROR
        job.error = str(exc)

