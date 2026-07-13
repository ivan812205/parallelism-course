from datetime import UTC, datetime

from clickhouse_connect.driver import AsyncClient
from clickhouse_connect import get_async_client

from samokat.config import ClickHouseConfig


class ClickHouseManager:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def close(self) -> None:
        close_result = self.client.close()

        if close_result is not None:
            await close_result

    async def insert(self, table_name: str, columns: list[str], data: list):
        await self.client.insert(table_name, data, column_names=columns)

    async def insert_user_event(
        self,
        user_id: int,
        event: str,
        category: str,
        event_time: datetime,
    ) -> None:
        await self.insert(
            table_name="user_events",
            columns=[
                "user_id",
                "event",
                "category",
                "event_time",
                "created_time",
            ],
            data=[
                [
                    user_id,
                    event,
                    category,
                    event_time,
                    datetime.now(UTC),
                ],
            ],
        )


async def create_clickhouse_manager(
    config: ClickHouseConfig,
) -> ClickHouseManager:
    client = await get_async_client(
        host=config.host,
        port=config.port,
        username=config.username,
        password=config.password.get_secret_value(),
        database=config.database,
        secure=config.secure,
        compress=config.compress,
    )

    return ClickHouseManager(client)
