from fastapi import APIRouter, Depends, Header, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session


from crud.users import (
    AppException,
    authenticate_user,
    create_access_token,
    create_user,
    decode_access_token,
    delete_user,
    get_user_by_id,
    get_users,
    update_user,
    get_current_user_role_data,
)
from database import get_db
from dependencies import get_current_user, get_admin_user
from schemas.users import Message, Token, UserCreate, UserLogin, UserOut, UserUpdate ,UserRoleResponse
from models import User


router = APIRouter(prefix="/api/v1/users", tags=["Authentication & Users"])

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user_in)


@router.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Note: OAuth2PasswordRequestForm uses 'username' field, so we pass it to email
    user = authenticate_user(db, form_data.username, form_data.password)
    token = create_access_token({"id": user.id, "email": user.email, "role": user.role})
    return {"access_token": token, "token_type": "bearer"}



@router.get("/", response_model=list[UserOut])
def list_users(
    db: Session = Depends(get_db),
    admin_user = Depends(get_admin_user)
):
    return get_users(db)


@router.get("/me", response_model=UserOut)
def read_current_user(current_user=Depends(get_current_user)):
    return current_user


@router.get("/{user_id}", response_model=UserOut)
def read_user(user_id: int, current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    return get_user_by_id(db, user_id)


@router.put("/edit", response_model=UserOut)
def edit_user(user_in: UserUpdate, current_user: User = Depends(get_current_user) ,  db: Session = Depends(get_db)):
    return update_user(db, user_in, current_user)


@router.delete("/{user_id}", response_model=Message)
def remove_user(user_id: int, current_user: User = Depends(get_admin_user), db: Session = Depends(get_db)):
    if current_user.id == user_id:
        raise AppException(status.HTTP_401_UNAUTHORIZED, "Cannot delete admin account")

    return delete_user(db, user_id)

@router.get("/me/role", response_model=UserRoleResponse)
def get_my_role(current_user: User = Depends(get_current_user)):
    return get_current_user_role_data(current_user)

