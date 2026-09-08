class DomainError(Exception):
    """Базовая ошибка бизнес-правил. Транслируется в HTTP в api/exceptions.py."""


class EventError(DomainError):
    pass


class EventNotFoundError(EventError):
    pass


class LocationError(DomainError):
    pass


class LocationNotFoundError(LocationError):
    pass


class BookingError(DomainError):
    pass


class BookingNotFoundError(BookingError):
    pass


class SeatsNotFoundError(BookingError):
    """Хотя бы одно из выбранных мест не существует у этого мероприятия."""


class SeatsUnavailableError(BookingError):
    """Хотя бы одно из выбранных мест уже занято (конкурентная бронь)."""


class BookingNotPayableError(BookingError):
    """Бронь нельзя оплатить: не в статусе ожидания оплаты или срок брони истёк."""


class PaymentUnavailableError(BookingError):
    """Payment API не отдал ответ даже после ретраев — операцию не завершить."""
