import logging
from contextlib import asynccontextmanager

from dishka import AsyncContainer
from fastapi import FastAPI

logger = logging.getLogger(__name__)


def create_lifespan(container: AsyncContainer):
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        logger.info("Delivery analytics lifespan started")

        try:
            yield
        finally:
            logger.info("Delivery analytics shutdown started")
            await container.close()

    return lifespan
