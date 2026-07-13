from fastapi import APIRouter
from samokat.api.routes.auth import router as auth_router
from samokat.api.routes.cart import router as cart_router
from samokat.api.routes.order import router as order_router
from samokat.api.routes.product import router as product_router
from samokat.api.routes.address import router as address_router

__all__ = ("main_router",)

main_router = APIRouter()

main_router.include_router(auth_router)
main_router.include_router(cart_router)
main_router.include_router(order_router)
main_router.include_router(product_router)
main_router.include_router(address_router)
