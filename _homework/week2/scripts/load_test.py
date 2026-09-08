"""Лестница нагрузки по ручкам «Афиши»: гоняет oha и печатает таблицу метрик.

Запуск: uv run python scripts/load_test.py [--port 8000]
Требуется установленный oha (brew install oha).
"""

import argparse
import json
import subprocess
import time

DURATION = "10s"
CONCURRENCY_LADDER = (1, 10, 50, 100, 200)
ENDPOINTS = {
    "GET /events": ("/events", []),
    "GET /events/{id}": ("/events/1", []),
    "GET /events/{id}/seats": ("/events/1/seats", []),
    "GET /organizer/events/{id}/dashboard": (
        "/organizer/events/1/dashboard",
        ["-H", "X-User-Id: 1"],
    ),
}


def run_oha(base_url: str, path: str, extra_args: list[str], connections: int) -> dict:
    command = [
        "oha", "-z", DURATION, "-c", str(connections), "--no-tui",
        "--output-format", "json", *extra_args, f"{base_url}{path}",
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    return json.loads(completed.stdout)


def as_millis(value: float | None) -> str:
    return "—" if value is None else str(round(value * 1000, 1))


def main() -> None:
    parser = argparse.ArgumentParser(description="Нагрузочные тесты ручек «Афиши»")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    arguments = parser.parse_args()
    base_url = f"http://{arguments.host}:{arguments.port}"

    print(f"{'ручка':38} {'c':>4} {'rps':>7} {'avg':>8} {'p95':>8} {'p99':>8}  коды")
    for title, (path, extra_args) in ENDPOINTS.items():
        for connections in CONCURRENCY_LADDER:
            report = run_oha(base_url, path, extra_args, connections)
            summary = report["summary"]
            latency = report["latencyPercentiles"]
            requests_per_sec = summary["requestsPerSec"]
            print(
                f"{title:38} {connections:>4} "
                f"{('—' if requests_per_sec is None else round(requests_per_sec)):>7} "
                f"{as_millis(summary['average']):>8} "
                f"{as_millis(latency.get('p95')):>8} "
                f"{as_millis(latency.get('p99')):>8}  "
                f"{report['statusCodeDistribution']}",
                flush=True,
            )
            time.sleep(2)


if __name__ == "__main__":
    main()
