from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import BookingStatus, SeatStatus

_FROZEN = ConfigDict(frozen=True)
_FROM_ORM = ConfigDict(from_attributes=True, frozen=True)


# --- справочные данные (чтение) ---
class LocationData(BaseModel):
    model_config = _FROM_ORM

    id: int
    name: str
    city: str
    address: str


class SeatData(BaseModel):
    model_config = _FROZEN

    id: int
    location_id: int
    sector: str
    row: int
    number: int
    x: int
    y: int


class LocationDetailData(BaseModel):
    model_config = _FROZEN

    location: LocationData
    seats: list[SeatData]


class EventData(BaseModel):
    model_config = _FROM_ORM

    id: int
    organizer_id: int
    location_id: int
    title: str
    description: str | None
    category: str
    starts_at: datetime
    base_price: int


class EventSeatData(BaseModel):
    model_config = _FROZEN

    id: int
    event_id: int
    seat_id: int
    sector: str
    row: int
    number: int
    x: int
    y: int
    price: int
    status: SeatStatus
    reserved_until: datetime | None
    booking_id: int | None


# --- бронирование (запись) ---
class LockedSeatData(BaseModel):
    model_config = _FROZEN

    id: int
    seat_id: int
    status: SeatStatus
    price: int


class BookingData(BaseModel):
    model_config = _FROM_ORM

    id: int
    event_id: int
    user_id: int
    amount: int
    payment_commission: int
    protection_price: int | None
    with_protection: bool
    status: BookingStatus
    reserved_until: datetime


# --- ответы внешних API (результат коннекторов) ---
class PaymentQuoteData(BaseModel):
    model_config = _FROZEN

    commission: int
    total: int
    payment_methods: list[str]
    expires_at: datetime | None = None


class ProtectionQuoteData(BaseModel):
    model_config = _FROZEN

    available: bool
    price: int
    covered_amount: int
    description: str | None = None


# --- результаты сценариев (возвращают сервисы, отдаёт API) ---
class CheckoutSeatData(BaseModel):
    model_config = _FROZEN

    id: int
    seat_id: int
    price: int


class CheckoutBookingData(BaseModel):
    model_config = _FROZEN

    id: int
    event_title: str
    starts_at: datetime
    seats: list[CheckoutSeatData]
    base_amount: int
    payment_commission: int
    protection_price: int | None
    with_protection: bool
    reserved_until: datetime


class CheckoutResultData(BaseModel):
    model_config = _FROZEN

    booking: CheckoutBookingData
    payment: PaymentQuoteData
    protection: ProtectionQuoteData | None


class SalesData(BaseModel):
    model_config = _FROZEN

    paid_orders: int
    sold_tickets: int
    revenue: int
    average_order: int


class OccupancyData(BaseModel):
    model_config = _FROZEN

    total: int
    available: int
    reserved: int
    sold: int
    occupancy_percent: float


class DashboardData(BaseModel):
    model_config = _FROZEN

    event_title: str
    starts_at: datetime
    sales: SalesData
    occupancy: OccupancyData


class PaymentResultData(BaseModel):
    model_config = _FROZEN

    booking_id: int
    status: BookingStatus
    charged_amount: int
    transaction_id: str
