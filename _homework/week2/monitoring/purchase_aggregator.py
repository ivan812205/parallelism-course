from monitoring.dto import PaymentActivityData, PurchaseEventData


class PurchaseAggregator:
    """Сворачивает покупки батча по мероприятиям: одно мероприятие — один агрегат."""

    def aggregate(self, events: list[PurchaseEventData]) -> list[PaymentActivityData]:
        payments: dict[int, list[int]] = {}
        for event in events:
            totals = payments.setdefault(event.event_id, [0, 0, 0])
            totals[0] += 1
            totals[1] += event.tickets_count
            totals[2] += event.total_amount
        return [
            PaymentActivityData(
                event_id=event_id,
                payments_count=payments_count,
                tickets_count=tickets_count,
                total_amount=total_amount,
            )
            for event_id, (payments_count, tickets_count, total_amount) in payments.items()
        ]
