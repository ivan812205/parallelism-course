Через Docker Compose можно поднять базу, API платежей и API страховки:

```bash
docker compose up -d db payment-api protection-api
```

База будет доступна на порту `7432`, API платежей (`payment`) на `9001`, API страховки (`protection`) на `9002`.

## Запуск (ДЗ 3-5)

Инфраструктура — база, pgbouncer, Redis, моки внешних API, Kafka с топиком
`tickets.purchased`:

```bash
docker compose up -d db pgbouncer redis payment-api protection-api kafka kafka-init
uv run alembic upgrade head
```

Приложения ходят в базу не напрямую, а через pgbouncer на порт `6432` (сама база
слушает `7432` и нужна для psql и разбора). Пулер работает в режиме transaction:
реальное соединение отдаётся клиенту на одну транзакцию, поэтому сотни клиентских
соединений живут на 25 серверных. Из-за этого режима серверные подготовленные
запросы выключены (`prepare_threshold=None` у psycopg) — иначе следующий клиент
получит «prepared statement _pg3_0 already exists».

Что происходит внутри пулера, видно в его служебной базе:

```bash
docker compose exec -e PGPASSWORD=postgres db \
  psql -h pgbouncer -p 6432 -U postgres -d pgbouncer -c "SHOW POOLS"
```

`cl_active` — сколько клиентов работают, `cl_waiting` — сколько ждут соединения,
`sv_active` — сколько реальных соединений занято в базе.

Приложение и фоновые воркеры taskiq (каждая очередь — свой процесс):

```bash
uv run uvicorn app.main:app --reload
uv run taskiq worker app.tasks.worker:reports_broker        # генерация PDF-отчётов
uv run taskiq worker app.tasks.worker:external_broker       # дорасчёт страховки
uv run taskiq worker app.tasks.worker:maintenance_broker    # регламентные задачи
uv run taskiq scheduler app.tasks.scheduler:scheduler       # расписание, раз в минуту
```

Готовые PDF-отчёты складываются в каталог `reports/` (на проде это было бы S3).

Воркеру дорасчёта страховки имеет смысл дать бюджет ожидания больше, чем ручке
оформления: пользователь ждать не должен, а фон может, например
`PROTECTION__TIMEOUT=8 uv run taskiq worker app.tasks.worker:external_broker`.

Под нагрузкой приложение запускается несколькими процессами — по замеру ДЗ 6
четыре воркера дают 2200 запросов/с против 905 у одного:

```bash
PURCHASE_GENERATOR__ENABLED=false uv run uvicorn app.main:app --workers 4
```

Генератор покупок живёт в lifespan, поэтому без этого флага он поднимется в каждом
воркере и поток событий в Kafka умножится на число процессов. Сумма пулов тоже
считается на все процессы: воркеры × (`pool_size` + `max_overflow`) должно оставаться
меньше `max_connections` базы.

## Сервис мониторинга покупок (ДЗ 5)

Второе приложение читает события `tickets.purchased` из Kafka батчами, агрегирует их
по мероприятиям, пишет в свою таблицу `event_payment_activity` и раздаёт агрегаты
менеджерам по WebSocket:

```bash
uv run uvicorn monitoring.main:app --port 8001
```

Поток активности — `ws://localhost:8001/ws/payments`, сообщения вида
`{"type": "payment_activity", "items": [{"event_id": 3, "payments_count": 3, ...}]}`.

Генератор тестовых покупок поднимается вместе с основным приложением. Его можно
выключить или ускорить через переменные окружения, например
`PURCHASE_GENERATOR__ENABLED=false` или `PURCHASE_GENERATOR__BURST_SIZE=40`.

## Нагрузочные тесты (ДЗ 6)

Лестница нагрузки по ручкам гоняется скриптом (нужен `oha`, ставится через
`brew install oha`):

```bash
uv run python scripts/load_test.py --port 8000
```

Результаты замеров, найденные узкие места и внесённые правки — в
[docs/load_testing.md](docs/load_testing.md).
