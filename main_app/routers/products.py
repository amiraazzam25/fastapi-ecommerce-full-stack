from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session 

from database import get_db
from schemas.products import *
from crud.products import * 
from dependencies import *
from models import *

router = APIRouter(prefix="/api/v1/products", tags=["Products"])

# Admin only: create product
@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def add_product(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    new_product = create_product(db, product)

    if new_product == "invalid_category":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category does not exist"
        )

    if new_product == "duplicate_product":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product already exists in this category"
        )

    return new_product

@router.get("", response_model=list[ProductResponse])
def read_products(
    hide_out_of_stock: bool = Query(False, description="Hide out-of-stock products"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Products per page"),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size

    return get_products_with_stock_filter(
        db=db,
        hide_out_of_stock=hide_out_of_stock,
        skip=skip,
        limit=page_size
    )

@router.get("/search", response_model=list[ProductResponse])
def search_products(
    name: str = Query(..., min_length=1, description="Search by product name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Products per page"),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size

    return search_products_by_name(
        db=db,
        name=name,
        skip=skip,
        limit=page_size
    )

@router.get("/admin/stock", response_model=list[ProductStockResponse])
def read_products_stock_admin(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Products per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    skip = (page - 1) * page_size

    return get_products_stock_admin(
        db=db,
        skip=skip,
        limit=page_size
    )

@router.get("/{product_id}", response_model=ProductResponse)
def read_product(product_id: int, db: Session = Depends(get_db)):
    product = get_product_by_id(db, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return product

@router.get("/by-category/{category_id}", response_model=list[ProductResponse])
def read_products_by_category(
    category_id: int,
    hide_out_of_stock: bool = Query(False, description="Hide out-of-stock products"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Products per page"),
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size

    return get_products_by_category(
        db=db,
        category_id=category_id,
        hide_out_of_stock=hide_out_of_stock,
        skip=skip,
        limit=page_size
    )

@router.put("/{product_id}", response_model=ProductResponse, status_code=status.HTTP_200_OK)
def edit_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    updated_product = update_product(db, product_id, product_data)

    if not updated_product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    if updated_product == "invalid_category":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category does not exist"
        )

    return updated_product

@router.delete("/{product_id}", response_model=ProductDeleteResponse, status_code=status.HTTP_200_OK)
def remove_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin_user)
):
    product = delete_product(db, product_id)

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    return ProductDeleteResponse(
        message="Product deleted successfully",
        deleted_product=product
    )
    
