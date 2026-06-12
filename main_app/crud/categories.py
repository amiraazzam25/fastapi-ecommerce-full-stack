from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from models import Category
from schemas.categories import CategoryCreate, CategoryUpdate
from core.logging_config import logger


def get_category_by_name(db: Session, name: str, exclude_category_id: int | None = None):
    normalized_name = name.strip()
    query = db.query(Category).filter(func.lower(Category.name) == normalized_name.lower())

    if exclude_category_id is not None:
        query = query.filter(Category.id != exclude_category_id)

    return query.first()


def create_category(db: Session, category: CategoryCreate):
    category_name = category.name.strip()

    if get_category_by_name(db, category_name):
        return "duplicate_category"

    db_category = Category(
        name=category_name,
        description=category.description
    )
    db.add(db_category)

    try:
        db.commit()
        db.refresh(db_category)
        logger.info(f"Category created: {db_category.name}")
    except IntegrityError:
        db.rollback()
        logger.error(f"Failed to create category (duplicate): {category_name}")
        return "duplicate_category"

    return db_category


def get_categories(db: Session):
    return db.query(Category).all()


def get_category_by_id(db: Session, category_id: int):
    return db.query(Category).filter(Category.id == category_id).first()


def update_category(db: Session, category_id: int, update_data: CategoryUpdate):
    category = db.query(Category).filter(Category.id == category_id).first()

    if not category:
        return None

    update_fields = update_data.dict(exclude_unset=True)

    if "name" in update_fields and update_fields["name"] is not None:
        category_name = update_fields["name"].strip()

        if get_category_by_name(db, category_name, exclude_category_id=category_id):
            return "duplicate_category"

        update_fields["name"] = category_name

    for key, value in update_fields.items():
        setattr(category, key, value)

    try:
        db.commit()
        db.refresh(category)
        logger.info(f"Category updated: {category.id}")
    except IntegrityError:
        db.rollback()
        logger.error(f"Failed to update category {category.id} (duplicate)")
        return "duplicate_category"

    return category


def delete_category(db: Session, category_id: int):
    category = db.query(Category).filter(Category.id == category_id).first()

    if not category:
        return None

    db.delete(category)
    db.commit()
    logger.warning(f"Category deleted: {category.id}")
    return category
