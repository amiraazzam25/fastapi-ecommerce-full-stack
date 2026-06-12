import redis.asyncio as redis
from fastapi import Header, Depends, status
from sqlalchemy.orm import Session

from database import get_db
from crud.users import AppException, decode_access_token, get_user_by_id
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login")

async def get_redis():
    client = redis.from_url("redis://redis:6379")
    try:
        yield client
    finally:
        await client.aclose()
        
from core.logging_config import logger

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = decode_access_token(token)
    except AppException as exc:
        logger.warning("Token validation failed: Invalid or expired token")
        raise exc
    
    user_id = payload.get("id") 
    if not user_id:
        logger.warning("Token validation failed: Missing user ID in payload")
        raise AppException(status.HTTP_401_UNAUTHORIZED, "Invalid token payload")

    return get_user_by_id(db, int(user_id))

def get_admin_user(current_user = Depends(get_current_user)):
    if current_user.role != "admin":
        logger.warning(f"Authorization failed: User {current_user.email} attempted to access admin route")
        raise AppException(status.HTTP_403_FORBIDDEN, "Admin privileges required")
    return current_user
