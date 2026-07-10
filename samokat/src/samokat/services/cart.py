import logging
from datetime import UTC, datetime

from samokat.application.dto import CartData, CartItemDetailsData
from samokat.infrastructure.clickhouse.manager import ClickHouseManager
from samokat.infrastructure.postgres.manager import DatabaseManager

logger = logging.getLogger(__name__)


class CartService:
    def __init__(
        self,
        db: DatabaseManager,
        clickhouse: ClickHouseManager,
    ) -> None:
        self.db = db
        self.clickhouse = clickhouse

    async def add_item(
        self,
        user_id: int,
        product_id: int,
        quantity: int,
    ) -> None:
        category = await self.db.products.get_product_category_title(product_id)

        await self.db.cart_items.add_cart_item(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
        )
        await self.db.commit()

        event_category = category or "unknown"
        try:
            await self.clickhouse.insert_user_event(
                user_id=user_id,
                event="cart_item_added",
                category=event_category,
                event_time=datetime.now(UTC),
            )
        except Exception:
            logger.exception(
                "Failed to write cart item added event to ClickHouse",
                extra={
                    "user_id": user_id,
                    "category": event_category,
                },
            )

    async def update_item_quantity(
        self,
        user_id: int,
        product_id: int,
        quantity: int,
    ) -> None:
        await self.db.cart_items.update_cart_item_quantity(
            user_id=user_id,
            product_id=product_id,
            quantity=quantity,
        )
        await self.db.commit()

    async def get_cart(
        self,
        user_id: int,
    ) -> CartData:
        cart_items = await self.db.cart_items.get_user_cart_items(user_id)
        items = [
            CartItemDetailsData(
                product_id=item.product_id,
                title=item.title,
                price=item.price,
                quantity=item.quantity,
                total_price=item.price * item.quantity,
            )
            for item in cart_items
        ]

        return CartData(
            items=items,
            products_price=sum(item.total_price for item in items),
        )
