from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session
from database import get_db

from schemas.categories import CategoryCreate, CategoryUpdate, CategoryResponse, CategoryWithProducts
# Import CRUD functions
from crud.categories import (
    create_category,
    get_categories,
    get_category_by_id,
    update_category,
    delete_category,
)
from dependencies import get_admin_user

router = APIRouter(
    prefix="/api/v1/categories",
    tags=["Categories"]
)


@router.post("/add", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def add_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    new_category = create_category(db, category)

    if new_category == "duplicate_category":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category with this name already exists"
        )

    return new_category


@router.get("/getall", response_model=list[CategoryResponse])
def read_categories(db: Session = Depends(get_db)):
    return get_categories(db)


@router.get("/{category_id}", response_model=CategoryWithProducts)
def read_category(category_id: int, db: Session = Depends(get_db)):
    category = get_category_by_id(db, category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return category


@router.put("/{category_id}", response_model=CategoryResponse)
def edit_category(
    category_id: int,
    update_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    category = update_category(db, category_id, update_data)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    if category == "duplicate_category":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category with this name already exists"
        )

    return category


@router.delete("/{category_id}")
def remove_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_admin_user)
):
    category = delete_category(db, category_id)

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    return {"message": "Category deleted"}
