from pydantic import BaseModel,Field
from typing import List, Optional
from schemas.shopping_cart import CartItem ## 
from datetime import datetime

class OrderCreate(BaseModel):
  user_id:int
  items: List[CartItem]


class OrderItem(BaseModel):
  order_id: int
  product_id: Optional[int]
  quantity: int 
  price_at_time_of_purchase: float
  class Config:
    from_attributes = True


class OrderResponse(BaseModel):
  id: int 
  user_id: Optional[int]
  items: List[OrderItem]
  total_price: float
  status: str = Field(...,max_length=20)
  created_at: datetime 
  class Config:
    from_attributes = True