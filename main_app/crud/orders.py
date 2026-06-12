from models import Order, OrderItem,Product
from schemas.orders import OrderCreate
from sqlalchemy.orm import Session
from schemas.shopping_cart import CartResponse
from core.logging_config import logger

def add_order(db:Session,order_data:CartResponse):
  total_price = 0
  order_list = []

  ## add order to order list to get the ID for the order items
  new_order = Order(user_id= order_data.user_id,total_price = total_price,)
  db.add(new_order)
  db.flush()  

  for item in order_data.items:
    product = db.query(Product).filter(Product.id == item.product_id).first()
    if not product:
      raise ValueError
    if product.stock < item.quantity:
      raise ValueError
    total_price += product.price*item.quantity
    order_item = OrderItem(
      order_id= new_order.id,
      product_id= product.id,
      quantity=item.quantity,
      price_at_time_of_purchase= product.price
    )
    order_list.append(order_item)
    product.stock = product.stock - order_item.quantity
    
  ## adding the list to database
  new_order.total_price = total_price
  db.add_all(order_list)
  db.commit()
  db.refresh(new_order)
  logger.info(f"Order created: {new_order.id} for user: {new_order.user_id}")
  return new_order

def get_user_orders(user_id:int,db:Session): 
  orders = db.query(Order).filter(Order.user_id == user_id).all()
  return orders


def get_all_orders(db:Session):
  all_orders = db.query(Order)
  return all_orders


def cancel_order(db: Session, order_id: int, user_id: int = None):
    query = db.query(Order).filter(Order.id == order_id)
    
    if user_id:
      query = query.filter(Order.user_id == user_id)
        
    order = query.first()
    
    if not order:
      return False
    if order.status == 'pending':
      order.status = 'canceled'
      for item in order.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        product.stock = product.stock + item.quantity
      db.commit()
      logger.info(f"Order {order_id} canceled successfully")
      return True
    logger.warning(f"Failed to cancel order {order_id}: status is {order.status}")
    return False

def change_to_shipping(db:Session,order_id:int):
  order = db.query(Order).filter(Order.id == order_id).first()
  if order and order.status == "pending":
    order.status = "shipped"
    db.commit()
    logger.info(f"Order {order_id} status changed to shipped")
    return True
  logger.warning(f"Failed to change order {order_id} to shipping")
  return False
