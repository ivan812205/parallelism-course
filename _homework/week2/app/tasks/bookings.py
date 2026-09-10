from dishka.integrations.taskiq import FromDishka, inject

from app.services.expired_booking_cleaner import ExpiredBookingCleaner
from app.tasks.brokers import maintenance_broker


@maintenance_broker.task(
    task_name="bookings.release_expired",
    schedule=[{"cron": "* * * * *"}],
)
@inject
async def release_expired_bookings(cleaner: FromDishka[ExpiredBookingCleaner]) -> int:
    """Раз в минуту: освободить места и удалить неоплаченные брони с истёкшим резервом."""
    return await cleaner.release_expired()
