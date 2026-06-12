"""
test_products.py — CRUD operations for Products and Categories.
                   Covers admin-only creation, public reads, updates,
                   deletion, duplicates, and missing-resource errors.
"""

import pytest

def _register_and_login(client, username, email, role="user"):
    client.post(
        "/api/v1/users/register",
        json={"username": username, "email": email, "password": "pass1234", "role": role},
    )
    resp = client.post(
        "/api/v1/users/login",
        data={"username": email, "password": "pass1234"},
    )
    return resp.json()["access_token"]


def _create_category(client, admin_token, name="Electronics"):
    resp = client.post(
        "/api/v1/categories/add",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": name, "description": "Test category"},
    )
    return resp


def _create_product(client, admin_token, category_id, name="Laptop"):
    return client.post(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": name,
            "description": "A great laptop",
            "price": 999.99,
            "stock": 10,
            "category_id": category_id,
        },
    )

def test_create_category_as_admin(client):
    token = _register_and_login(client, "prodadmin", "prodadmin@test.com", "admin")
    resp = _create_category(client, token, "Computers")
    assert resp.status_code == 201
    assert resp.json()["name"] == "Computers"


def test_create_category_as_user_forbidden(client):
    token = _register_and_login(client, "produser", "produser@test.com", "user")
    resp = _create_category(client, token, "ShouldFail")
    assert resp.status_code == 403


def test_create_duplicate_category(client):
    token = _register_and_login(client, "prodadmin2", "prodadmin2@test.com", "admin")
    _create_category(client, token, "Duplicated")
    resp = _create_category(client, token, "Duplicated")
    assert resp.status_code == 409


def test_get_all_categories(client):
    resp = client.get("/api/v1/categories/getall")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_category_by_id(client):
    token = _register_and_login(client, "prodadmin3", "prodadmin3@test.com", "admin")
    create_resp = _create_category(client, token, "Gadgets")
    cat_id = create_resp.json()["id"]

    resp = client.get(f"/api/v1/categories/{cat_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == cat_id


def test_get_nonexistent_category(client):
    resp = client.get("/api/v1/categories/999999")
    assert resp.status_code == 404


def test_update_category(client):
    token = _register_and_login(client, "prodadmin4", "prodadmin4@test.com", "admin")
    create_resp = _create_category(client, token, "UpdateMe")
    cat_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/v1/categories/{cat_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "UpdatedCategory"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "UpdatedCategory"


def test_delete_category(client):
    token = _register_and_login(client, "prodadmin5", "prodadmin5@test.com", "admin")
    create_resp = _create_category(client, token, "DeleteMe")
    cat_id = create_resp.json()["id"]

    resp = client.delete(
        f"/api/v1/categories/{cat_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

def test_create_product_as_admin(client):
    token = _register_and_login(client, "prodc_admin", "prodc_admin@test.com", "admin")
    cat_resp = _create_category(client, token, "ProdCategory")
    cat_id = cat_resp.json()["id"]

    resp = _create_product(client, token, cat_id, "Keyboard")
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Keyboard"
    assert data["price"] == 999.99


def test_create_product_as_user_forbidden(client):
    user_token = _register_and_login(client, "prodc_user", "prodc_user@test.com", "user")
    resp = _create_product(client, user_token, 1, "ForbiddenProduct")
    assert resp.status_code == 403


def test_create_product_invalid_category(client):
    token = _register_and_login(client, "prodc_admin2", "prodc_admin2@test.com", "admin")
    resp = _create_product(client, token, 999999, "GhostProduct")
    assert resp.status_code == 400


def test_create_duplicate_product_in_same_category(client):
    token = _register_and_login(client, "prodc_admin3", "prodc_admin3@test.com", "admin")
    cat_resp = _create_category(client, token, "DupProdCat")
    cat_id = cat_resp.json()["id"]

    _create_product(client, token, cat_id, "Mouse")
    resp = _create_product(client, token, cat_id, "Mouse")
    assert resp.status_code == 409


def test_get_all_products(client):
    resp = client.get("/api/v1/products")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_get_product_by_id(client):
    token = _register_and_login(client, "prodc_admin4", "prodc_admin4@test.com", "admin")
    cat_resp = _create_category(client, token, "SingleProdCat")
    cat_id = cat_resp.json()["id"]

    prod_resp = _create_product(client, token, cat_id, "Monitor")
    prod_id = prod_resp.json()["id"]

    resp = client.get(f"/api/v1/products/{prod_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == prod_id


def test_get_nonexistent_product(client):
    resp = client.get("/api/v1/products/999999")
    assert resp.status_code == 404


def test_update_product(client):
    token = _register_and_login(client, "prodc_admin5", "prodc_admin5@test.com", "admin")
    cat_resp = _create_category(client, token, "UpdateProdCat")
    cat_id = cat_resp.json()["id"]
    prod_resp = _create_product(client, token, cat_id, "Headphones")
    prod_id = prod_resp.json()["id"]

    resp = client.put(
        f"/api/v1/products/{prod_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Premium Headphones", "price": 149.99},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Premium Headphones"


def test_delete_product(client):
    token = _register_and_login(client, "prodc_admin6", "prodc_admin6@test.com", "admin")
    cat_resp = _create_category(client, token, "DeleteProdCat")
    cat_id = cat_resp.json()["id"]
    prod_resp = _create_product(client, token, cat_id, "Webcam")
    prod_id = prod_resp.json()["id"]

    resp = client.delete(
        f"/api/v1/products/{prod_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_search_products(client):
    resp = client.get("/api/v1/products/search?name=Key")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)