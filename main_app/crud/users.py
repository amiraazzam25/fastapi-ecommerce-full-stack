from datetime import datetime, timedelta, timezone
import os
from fastapi import HTTPException, status, Depends, Header
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from database import load_dotenv
from core.logging_config import logger

import models 
from schemas.users import UserCreate, UserUpdate



load_dotenv()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))


class AppException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class DatabaseException(HTTPException):
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)



def hash_password(password: str) -> str:
    return pwd_context.hash(password)



def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)



def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token") from exc



def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()



def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()



def get_user_by_id(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise AppException(status.HTTP_404_NOT_FOUND, "User not found")
    return user



def get_users(db: Session):
    return db.query(models.User).order_by(models.User.id.asc()).all()



def create_user(db: Session, user_in: UserCreate):
    if get_user_by_email(db, user_in.email):
        raise AppException(status.HTTP_409_CONFLICT, "Email already registered")

    if get_user_by_username(db, user_in.username):
        raise AppException(status.HTTP_409_CONFLICT, "Username already exists")
    new_user = models.User(
        username=user_in.username,
        email=user_in.email,
        password=hash_password(user_in.password[:72]),
        created_at=datetime.now(timezone.utc),
        role=user_in.role
    )


    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        logger.info(f"New user registered: {new_user.email}")
        return new_user
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"Failed to create user {user_in.email}: {str(exc)}")
        raise DatabaseException("Failed to create user") from exc


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.password):
        logger.warning(f"Failed login attempt for email: {email}")
        raise AppException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    logger.info(f"User logged in successfully: {email}")

    return user


def update_user(db: Session, user_in: UserUpdate, user: models.User):

    if user_in.email and user_in.email != user.email:
        existing_email = get_user_by_email(db, user_in.email)
        if existing_email:
            raise AppException(status.HTTP_409_CONFLICT, "Email already registered")
        user.email = user_in.email

    if user_in.username and user_in.username != user.username:
        existing_username = get_user_by_username(db, user_in.username)
        if existing_username:
            raise AppException(status.HTTP_409_CONFLICT, "Username already exists")
        user.username = user_in.username

    if user_in.password:
        if not user_in.old_password:
            raise AppException(status.HTTP_400_BAD_REQUEST, "Old password is required")
        if not verify_password(user_in.old_password, user.password):
            raise AppException(status.HTTP_401_UNAUTHORIZED, "Invalid old password")
        if not user_in.confirm_password:
            raise AppException(status.HTTP_400_BAD_REQUEST, "Confirm password is required")
        if user_in.confirm_password != user_in.password:
            raise AppException(status.HTTP_400_BAD_REQUEST, "Passwords do not match")
        user.password = hash_password(user_in.password)

    try:
        db.commit()
        db.refresh(user)
        logger.info(f"User updated successfully: {user.email}")
        return user
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"Failed to update user {user.email}: {str(exc)}")
        raise DatabaseException("Failed to update user") from exc



def delete_user(db: Session, user_id: int):
    user = get_user_by_id(db, user_id)
    try:
        db.delete(user)
        db.commit()
        logger.info(f"User deleted successfully: ID {user_id}")
        return {"detail": "User deleted successfully"}
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"Failed to delete user {user_id}: {str(exc)}")
        raise DatabaseException("Failed to delete user") from exc


def get_current_user_role_data(current_user: models.User):
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }