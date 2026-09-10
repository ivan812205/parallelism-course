Через Docker Compose можно поднять базу, API платежей и API страховки:

```bash
docker compose up -d db payment-api protection-api
```

База будет доступна на порту `7432`, API платежей (`payment`) на `9001`, API страховки (`protection`) на `9002`.

## Запуск (ДЗ 3-4)

Инфраструктура — база, Redis, моки внешних API:

```bash
docker compose up -d db redis payment-api protection-api
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
