Через Docker Compose можно поднять базу, API платежей и API страховки:

```bash
docker compose up -d db payment-api protection-api
```

База будет доступна на порту `7432`, API платежей (`payment`) на `9001`, API страховки (`protection`) на `9002`.

## Запуск (ДЗ 3-5)

Инфраструктура — база, Redis, моки внешних API, Kafka с топиком `tickets.purchased`:

```bash
docker compose up -d db redis payment-api protection-api kafka kafka-init
uv run alembic upgrade head
```

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
