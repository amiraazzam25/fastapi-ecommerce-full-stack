"""
test_cart.py — Shopping cart CRUD operations.
               Tests get, add, update quantity, remove item, clear cart,
               stock-limit enforcement, and unauthorized access.
"""

import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

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


def _create_category(client, admin_token, name):
    resp = client.post(
        "/api/v1/categories/add",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": name, "description": "Cart test category"},
    )
    return resp.json()["id"]


def _create_product(client, admin_token, category_id, name, stock=10):
    resp = client.post(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": name,
            "description": "Cart test product",
            "price": 50.0,
            "stock": stock,
            "category_id": category_id,
        },
    )
    return resp.json()["id"]


# ── Cart tests ────────────────────────────────────────────────────────────────

def test_cart_unauthorized(client):
    """Accessing the cart without a token must return 401."""
    response = client.get("/api/v1/cart/")
    assert response.status_code in [401, 403]


def test_get_empty_cart(client):
    """A freshly-created user should have an empty cart."""
    token = _register_and_login(client, "cartuser", "cartuser@test.com")
    response = client.get(
        "/api/v1/cart/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total_price"] == 0.0


def test_add_to_cart(client):
    admin_token = _register_and_login(client, "cartadmin", "cartadmin@test.com", "admin")
    user_token  = _register_and_login(client, "cartbuyer", "cartbuyer@test.com", "user")

    cat_id  = _create_category(client, admin_token, "CartCat")
    prod_id = _create_product(client, admin_token, cat_id, "CartProd")

    response = client.post(
        "/api/v1/cart/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"product_id": prod_id, "quantity": 2},
    )
    assert response.status_code == 201
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["quantity"] == 2


def test_add_nonexistent_product_to_cart(client):
    token = _register_and_login(client, "cartbuyer2", "cartbuyer2@test.com")
    response = client.post(
        "/api/v1/cart/",
        headers={"Authorization": f"Bearer {token}"},
        json={"product_id": 999999, "quantity": 1},
    )
    assert response.status_code == 404


def test_add_exceeds_stock(client):
    """Adding more items than available stock must return 400."""
    admin_token = _register_and_login(client, "stockadmin", "stockadmin@test.com", "admin")
    user_token  = _register_and_login(client, "stockbuyer", "stockbuyer@test.com", "user")

    cat_id  = _create_category(client, admin_token, "StockLimitCat")
    prod_id = _create_product(client, admin_token, cat_id, "LimitedItem", stock=3)

    response = client.post(
        "/api/v1/cart/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"product_id": prod_id, "quantity": 10}, 
    )
    assert response.status_code == 400


def test_update_cart_item(client):
    admin_token = _register_and_login(client, "upd_admin", "upd_admin@test.com", "admin")
    user_token  = _register_and_login(client, "upd_buyer", "upd_buyer@test.com", "user")

    cat_id  = _create_category(client, admin_token, "UpdCat")
    prod_id = _create_product(client, admin_token, cat_id, "UpdProd")

    client.post(
        "/api/v1/cart/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"product_id": prod_id, "quantity": 1},
    )

    response = client.put(
        f"/api/v1/cart/{prod_id}",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"quantity": 5},
    )
    assert response.status_code == 200
    item = next(i for i in response.json()["items"] if i["product_id"] == prod_id)
    assert item["quantity"] == 5


def test_remove_from_cart(client):
    admin_token = _register_and_login(client, "rem_admin", "rem_admin@test.com", "admin")
    user_token  = _register_and_login(client, "rem_buyer", "rem_buyer@test.com", "user")

    cat_id  = _create_category(client, admin_token, "RemCat")
    prod_id = _create_product(client, admin_token, cat_id, "RemProd")

    client.post(
        "/api/v1/cart/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"product_id": prod_id, "quantity": 1},
    )

    response = client.delete(
        f"/api/v1/cart/{prod_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200
    assert all(i["product_id"] != prod_id for i in response.json()["items"])


def test_clear_cart(client):
    admin_token = _register_and_login(client, "clr_admin", "clr_admin@test.com", "admin")
    user_token  = _register_and_login(client, "clr_buyer", "clr_buyer@test.com", "user")

    cat_id  = _create_category(client, admin_token, "ClrCat")
    prod_id = _create_product(client, admin_token, cat_id, "ClrProd")

    client.post(
        "/api/v1/cart/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"product_id": prod_id, "quantity": 1},
    )

    response = client.delete(
        "/api/v1/cart/clear",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200