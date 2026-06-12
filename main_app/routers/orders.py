from fastapi import APIRouter, HTTPException, Depends,status
from sqlalchemy.orm import Session
from database import get_db
from dependencies import *
from models import *
from schemas.orders import * 
from crud.orders import * 
from crud.shopping_cart import get_cart,clear_cart
router = APIRouter(prefix='/api/v1/orders',tags=['Orders'])

@router.post('/create',response_model=OrderResponse,status_code=status.HTTP_201_CREATED)
async def create_order(db:Session =Depends(get_db),redis_client: redis.Redis = Depends(get_redis),current_user = Depends(get_current_user)):
  order_data = await get_cart(redis_client,current_user.id)
  if not order_data['items']:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shopping Cart is empty.")
  order_data = CartResponse(
        user_id=order_data["user_id"],
        items=order_data["items"],
        total_price=order_data['total_price']
    )
  try:
    new_order = add_order(db,order_data)
  except ValueError as e:
    raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="Could not create order. Please check product stock.")
  await clear_cart(redis_client,current_user.id)
  return new_order

@router.get('/get/user/{user_id}',response_model=List[OrderResponse])
def get_orders_by_id(user_id:int ,db:Session = Depends(get_db),is_admin=Depends(get_admin_user)):
  orders = get_user_orders(user_id,db)
  if not orders:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No orders found for this user")
  return orders


@router.get('/get/my_orders',response_model=List[OrderResponse])
def get_my_orders(current_user = Depends(get_current_user),db:Session = Depends(get_db)):
  orders = get_user_orders(current_user.id,db)
  if not orders:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No orders found")
  return orders

@router.get('/get_all_orders',response_model=List[OrderResponse])
def admin_order_panel(db:Session = Depends(get_db),is_admin = Depends(get_admin_user)):
  all_orders = get_all_orders(db)
  if not all_orders:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="No orders found")
  return all_orders


@router.delete('/cancel/{order_id}')
def delete_order(order_id:int,db: Session = Depends(get_db),current_user = Depends(get_current_user)):
  
  if current_user.role == 'admin':
    canceled = cancel_order(db,order_id)
    if not canceled:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Order not found or already shipped.")
    return {'messege':f'order {order_id} has been canceled'}
  else:
    canceled = cancel_order(db,order_id,current_user.id)
    if not canceled:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Order not found or already shipped")
    return {'messege':f'order {order_id} has been canceled'}
  
@router.put('/put/ship/{order_id}',status_code=status.HTTP_200_OK)
def ship_order(order_id:int,Session = Depends(get_db),is_admin = Depends(get_admin_user)):
  changed = change_to_shipping(Session,order_id)
  if not changed:
      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Order not found or already shipped.")
  