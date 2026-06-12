from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import redis.asyncio as redis
from database import get_db
from dependencies import get_current_user, get_redis
from schemas.shopping_cart import CartItem, CartItemAdd, CartItemUpdate, CartResponse
from crud import shopping_cart as cart_service
import models

router = APIRouter(prefix="/api/v1/cart", tags=["Cart"])


@router.get("/", response_model=CartResponse)
async def get_cart(
    redis_client: redis.Redis = Depends(get_redis),
    current_user: models.User = Depends(get_current_user),
):
    return await cart_service.get_cart(redis_client, current_user.id)


@router.post("/", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
async def add_to_cart(
    item: CartItemAdd,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_user: models.User = Depends(get_current_user),
):
    product = db.query(models.Product).filter(models.Product.id == item.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return await cart_service.add_to_cart(
        redis_client, current_user.id, item,
        product_price=float(product.price),
        product_name=product.name,
        product_stock=product.stock,
    )


@router.put("/{product_id}", response_model=CartResponse)
async def update_cart_item(
    product_id: int,
    update_data: CartItemUpdate,
    db: Session = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_user: models.User = Depends(get_current_user),
):
    product = db.query(models.Product).filter(models.Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return await cart_service.update_cart_item(
        redis_client, current_user.id, product_id, update_data, product_stock=product.stock
    )


@router.delete("/clear", status_code=status.HTTP_200_OK) 
async def clear_cart(
    redis_client: redis.Redis = Depends(get_redis),
    current_user: models.User = Depends(get_current_user),
):
    return await cart_service.clear_cart(redis_client, current_user.id)


@router.delete("/{product_id}", response_model=CartResponse)
async def remove_from_cart(
    product_id: int,
    redis_client: redis.Redis = Depends(get_redis),
    current_user: models.User = Depends(get_current_user),
):
    return await cart_service.remove_from_cart(redis_client, current_user.id, product_id)