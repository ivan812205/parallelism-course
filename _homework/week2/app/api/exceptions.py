from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

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


def _response_for(exc: DomainError) -> tuple[int, str]:
    for error_type, response in DOMAIN_ERROR_RESPONSES.items():
        if isinstance(exc, error_type):
            return response
    return status.HTTP_400_BAD_REQUEST, "Ошибка запроса"
