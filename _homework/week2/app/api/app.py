import asyncio

from dishka import AsyncContainer
from dishka.integrations.fastapi import setup_dishka
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.exceptions import setup_exception_handlers
from app.api.lifespan import create_lifespan
from app.api.routes import main_router
from app.config import Settings


def create_fastapi_app(settings: Settings, container: AsyncContainer) -> FastAPI:
    app = FastAPI(title="API Афиши", lifespan=create_lifespan(container))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def timeout_middleware(request: Request, call_next):
        # урок 9: общий таймаут бизнес-операции на уровне приложения
        try:
            async with asyncio.timeout(settings.app.request_timeout):
                return await call_next(request)
        except TimeoutError:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": "Сервис временно недоступен, попробуйте позже"},
            )

    setup_dishka(container=container, app=app)
    setup_exception_handlers(app)
    app.include_router(main_router)
    return app
