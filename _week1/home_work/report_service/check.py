import time

from fastapi.testclient import TestClient

from main import app


def check(client: TestClient):
    # запускаем отчёт — сразу получаем job_id, не дожидаясь 4 секунд
    job = client.post("/reports/1").json()
    print(f"POST /reports/1 -> {job}")

    # пока отчёт считается в фоне, пингуем и меряем время ответа
    for _ in range(8):
        start = time.perf_counter()
        client.get("/ping")
        print(f"ping: {time.perf_counter() - start:.4f}s")
        time.sleep(0.5)

    # ждём, пока отчёт добьётся, и забираем результат
    while True:
        result = client.get(f"/reports/jobs/{job['job_id']}").json()
        if result["status"] != "running":
            break
        time.sleep(0.5)
    print(f"GET /reports/jobs -> {result}")


if __name__ == '__main__':
    with TestClient(app) as client:
        check(client)
