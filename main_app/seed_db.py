import json
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from crud.users import create_user, get_user_by_email, AppException as UserAppException
from crud.categories import create_category, get_category_by_name
from crud.products import create_product
from schemas.users import UserCreate
from schemas.categories import CategoryCreate
from schemas.products import ProductCreate

def load_seed_data(filepath="seed_data.json"):
    with open(filepath, "r") as f:
        return json.load(f)

def seed_database():
    print("Starting database seeding...")
    db: Session = SessionLocal()
    
    try:
        print("Ensuring admin user exists...")
        admin_email = "admin@gmail.com"
        admin_username = "admin"
        existing_admin = get_user_by_email(db, admin_email)
        
        if not existing_admin:
            try:
                admin_user_data = UserCreate(
                    username=admin_username,
                    email=admin_email,
                    password="admin123",
                    role="admin",
                    confirm_password="admin123"
                )
                create_user(db, admin_user_data)
                print(f"Admin user '{admin_email}' created successfully.")
            except Exception as e:
                print(f"Failed to create admin user: {e}")
        else:
            print(f"Admin user '{admin_email}' already exists. Skipping.")

        data = load_seed_data()
        
        print("\nInserting categories...")
        category_map = {}
        for cat_data in data.get("categories", []):
            existing_cat = get_category_by_name(db, cat_data["name"])
            if existing_cat:
                print(f"Category '{cat_data['name']}' already exists.")
                category_map[cat_data["name"]] = existing_cat.id
            else:
                new_cat_schema = CategoryCreate(
                    name=cat_data["name"],
                    description=cat_data.get("description", "")
                )
                result = create_category(db, new_cat_schema)
                if result == "duplicate_category":
                    print(f"Category '{cat_data['name']}' is a duplicate.")
                else:
                    category_map[cat_data["name"]] = result.id
                    print(f"Created category: {cat_data['name']}")

        print("\nInserting products...")
        for prod_data in data.get("products", []):
            cat_name = prod_data.pop("category_name", None)
            
            cat_id = category_map.get(cat_name)
            if not cat_id:
                db_cat = get_category_by_name(db, cat_name)
                if db_cat:
                    cat_id = db_cat.id
                else:
                    print(f"Error: Category '{cat_name}' not found for product '{prod_data['name']}'. Skipping product.")
                    continue
            
            prod_data["category_id"] = cat_id
            
            new_prod_schema = ProductCreate(**prod_data)
            result = create_product(db, new_prod_schema)
            
            if result == "duplicate_product":
                print(f"Product '{prod_data['name']}' already exists. Skipping.")
            elif result == "invalid_category":
                print(f"Invalid category for product '{prod_data['name']}'. Skipping.")
            else:
                print(f"Created product: {prod_data['name']}")

        print("\nDatabase seeding completed successfully!")

    except Exception as e:
        print(f"An unexpected error occurred during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
