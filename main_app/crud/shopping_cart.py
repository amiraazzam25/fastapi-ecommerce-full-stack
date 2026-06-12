import json
import redis.asyncio as redis
from fastapi import HTTPException, status
from schemas.shopping_cart import CartItem, CartItemAdd, CartItemUpdate

CART_TTL = 60 * 60 * 24 * 7  # 7 days


def _cart_key(user_id: int) -> str:
    return f"cart:user:{user_id}"


async def get_cart(redis_client: redis.Redis, user_id: int) -> dict:
    key = _cart_key(user_id)
    cart_data = await redis_client.get(key)

    if not cart_data:
        return {"user_id": user_id, "items": [], "total_price": 0.0}

    return json.loads(cart_data)


async def add_to_cart(
    redis_client: redis.Redis,
    user_id: int,
    item: CartItemAdd,
    product_price: float,
    product_name: str,
    product_stock: int,
) -> dict:
    if item.quantity > product_stock:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough stock. Available: {product_stock}",
        )

    key = _cart_key(user_id)
    cart_data = await redis_client.get(key)
    cart = json.loads(cart_data) if cart_data else {"user_id": user_id, "items": []}

    # Check if product already in cart
    for existing_item in cart["items"]:
        if existing_item["product_id"] == item.product_id:
            new_qty = existing_item["quantity"] + item.quantity
            if new_qty > product_stock:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Total quantity exceeds stock. Available: {product_stock}",
                )
            existing_item["quantity"] = new_qty
            existing_item["subtotal"] = round(new_qty * product_price, 2)
            cart["total_price"] = _calc_total(cart["items"])
            await redis_client.setex(key, CART_TTL, json.dumps(cart))
            return cart

    # Add new item
    cart["items"].append({
        "product_id": item.product_id,
        "product_name": product_name,
        "quantity": item.quantity,
        "price": product_price,
        "subtotal": round(item.quantity * product_price, 2),
    })

    cart["total_price"] = _calc_total(cart["items"])
    await redis_client.setex(key, CART_TTL, json.dumps(cart))
    return cart


async def update_cart_item(
    redis_client: redis.Redis,
    user_id: int,
    product_id: int,
    update_data: CartItemUpdate,
    product_stock: int,
) -> dict:
    key = _cart_key(user_id)
    cart_data = await redis_client.get(key)

    if not cart_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart is empty",
        )

    cart = json.loads(cart_data)

    for item in cart["items"]:
        if item["product_id"] == product_id:
            if update_data.quantity > product_stock:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Not enough stock. Available: {product_stock}",
                )
            item["quantity"] = update_data.quantity
            item["subtotal"] = round(update_data.quantity * item["price"], 2)
            cart["total_price"] = _calc_total(cart["items"])
            await redis_client.setex(key, CART_TTL, json.dumps(cart))
            return cart

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Product not found in cart",
    )


async def remove_from_cart(
    redis_client: redis.Redis,
    user_id: int,
    product_id: int,
) -> dict:
    key = _cart_key(user_id)
    cart_data = await redis_client.get(key)

    if not cart_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart is empty",
        )

    cart = json.loads(cart_data)
    original_len = len(cart["items"])
    cart["items"] = [i for i in cart["items"] if i["product_id"] != product_id]

    if len(cart["items"]) == original_len:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in cart",
        )

    cart["total_price"] = _calc_total(cart["items"])
    await redis_client.setex(key, CART_TTL, json.dumps(cart))
    return cart


async def clear_cart(redis_client: redis.Redis, user_id: int) -> dict:
    key = _cart_key(user_id)
    await redis_client.delete(key)
    return {"detail": "Cart cleared successfully"}


def _calc_total(items: list) -> float:
    return round(sum(i["subtotal"] for i in items), 2)