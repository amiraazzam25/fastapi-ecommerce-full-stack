from pydantic import BaseModel, Field
from typing import List


class CartItem(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)


class CartItemUpdate(BaseModel):  
    quantity: int = Field(..., gt=0)


class CartItemInResponse(BaseModel): # final version of cart 
    product_id: int
    product_name: str
    quantity: int
    price: float
    subtotal: float


class CartResponse(BaseModel): # when I add item to cart 
    user_id: int
    items: List[CartItemInResponse]
    total_price: float