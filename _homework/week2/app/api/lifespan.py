from contextlib import asynccontextmanager

from dishka import AsyncContainer
from fastapi import FastAPI

from app.add_event_data import seed_event_data
from app.infrastructure.postgres.manager import PostgresClient


def create_lifespan(container: AsyncContainer):
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        postgres = await container.get(PostgresClient)
        async with postgres.session() as db:
            await seed_event_data(db.session)
        yield

    return lifespan
