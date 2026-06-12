from sqlalchemy.orm import Session 
from sqlalchemy import func , or_
from models import Product, Category
from schemas.products import ProductCreate,ProductUpdate
from core.logging_config import logger

def create_product(db: Session, product_data: ProductCreate):
    category = db.query(Category).filter(
        Category.id == product_data.category_id
    ).first()

    if not category:
        return "invalid_category"

    product_name = product_data.name.strip()

    existing_product = db.query(Product).filter(
        func.lower(Product.name) == product_name.lower(),
        Product.category_id == product_data.category_id
    ).first()

    if existing_product:
        return "duplicate_product"

    new_product = Product(
        name=product_name,
        description=product_data.description,
        price=product_data.price,
        stock=product_data.stock,
        img_path=product_data.img_path,
        category_id=product_data.category_id
    )

    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    logger.info(f"Product created: {new_product.name}")
    return new_product

def get_products_stock_admin(
    db: Session,
    skip: int = 0,
    limit: int = 10
):
    return (
        db.query(Product)
        .order_by(Product.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_all_products(db: Session):
    return db.query(Product).all()

def get_products_with_stock_filter(
    db: Session,
    hide_out_of_stock: bool = False,
    skip: int = 0,
    limit: int = 10
):
    query = db.query(Product).order_by(Product.id.asc())

    if hide_out_of_stock:
        query = query.filter(Product.stock > 0)

    return query.offset(skip).limit(limit).all()

def search_products_by_name(
    db: Session,
    name: str,
    skip: int = 0,
    limit: int = 10
):
    search_name = name.strip().lower()

    query = db.query(Product).filter(
        func.lower(Product.name).contains(search_name)
    ).order_by(Product.id.asc())

    return query.offset(skip).limit(limit).all()

def get_in_stock_products(db: Session):
    return db.query(Product).filter(Product.stock > 0).all()

def get_product_by_id(db: Session, product_id: int):
    return db.query(Product).filter(Product.id == product_id).first()

def get_products_by_category(
    db: Session,
    category_id: int,
    hide_out_of_stock: bool = False,
    skip: int = 0,
    limit: int = 10
):
    query = db.query(Product).filter(Product.category_id == category_id)

    if hide_out_of_stock:
        query = query.filter(Product.stock > 0)

    return (
        query
        .order_by(Product.id.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

def update_product(db: Session, product_id: int, product_data: ProductUpdate):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        return None

    update_data = product_data.model_dump(exclude_unset=True)

    if "category_id" in update_data:
        category = db.query(Category).filter(Category.id == update_data["category_id"]).first()
        if not category:
            return "invalid_category"

    for key, value in update_data.items():
        setattr(product, key, value)

    db.commit()
    db.refresh(product)
    logger.info(f"Product updated: {product.id}")
    return product

def delete_product(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        return None

    db.delete(product)
    db.commit()
    logger.warning(f"Product deleted: {product.id}")
    return product