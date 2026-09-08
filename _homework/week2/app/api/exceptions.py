import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from sqlalchemy.exc import TimeoutError as PoolTimeoutError

from app.domain.exceptions import (
    BookingNotFoundError,
    BookingNotPayableError,
    DomainError,
    EventNotFoundError,
    EventUnavailableError,
    LocationNotFoundError,
    PaymentUnavailableError,
    SeatsNotFoundError,
    SeatsUnavailableError,
)

logger = logging.getLogger(__name__)

OVERLOAD_MESSAGE = "Сервис перегружен, попробуйте позже"

DOMAIN_ERROR_RESPONSES: dict[type[DomainError], tuple[int, str]] = {
    EventNotFoundError: (status.HTTP_404_NOT_FOUND, "Мероприятие не найдено"),
    EventUnavailableError: (
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Мероприятие временно недоступно, попробуйте позже",
    ),
    LocationNotFoundError: (status.HTTP_404_NOT_FOUND, "Площадка не найдена"),
    BookingNotFoundError: (status.HTTP_404_NOT_FOUND, "Бронь не найдена"),
    SeatsNotFoundError: (status.HTTP_404_NOT_FOUND, "Некоторые места не найдены"),
    SeatsUnavailableError: (status.HTTP_409_CONFLICT, "Одно или несколько мест уже заняты"),
    BookingNotPayableError: (status.HTTP_409_CONFLICT, "Бронь нельзя оплатить (оплачена или просрочена)"),
    PaymentUnavailableError: (status.HTTP_502_BAD_GATEWAY, "Сервис платежей недоступен"),
}


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, exc: DomainError) -> JSONResponse:
        status_code, message = _response_for(exc)
        return JSONResponse(status_code=status_code, content={"detail": message})

    @app.exception_handler(PoolTimeoutError)
    async def handle_pool_timeout(request: Request, exc: PoolTimeoutError) -> JSONResponse:
        # пул соединений к базе исчерпан: это перегрузка, а не ошибка клиента (найдено в ДЗ 6)
        logger.warning("Пул соединений к PostgreSQL исчерпан на %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": OVERLOAD_MESSAGE},
        )

    @app.exception_handler(RedisError)
    async def handle_redis_error(request: Request, exc: RedisError) -> JSONResponse:
        logger.warning("Redis не отдал ответ на %s: %r", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": OVERLOAD_MESSAGE},
        )


def _response_for(exc: DomainError) -> tuple[int, str]:
    for error_type, response in DOMAIN_ERROR_RESPONSES.items():
        if isinstance(exc, error_type):
            return response
    # неизвестная доменная ошибка — это дефект бэкенда, а не плохой запрос клиента
    # (замечание ревью ДЗ 2: 400 говорит клиенту «данные невалидны», что тут неверно)
    return status.HTTP_500_INTERNAL_SERVER_ERROR, "Внутренняя ошибка сервиса"
