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


def _create_category(client, admin_token, name):
    resp = client.post(
        "/api/v1/categories/add",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"name": name, "description": "Order test category"},
    )
    return resp.json()["id"]


def _create_product(client, admin_token, category_id, name):
    resp = client.post(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "name": name,
            "description": "Order test product",
            "price": 100.0,
            "stock": 20,
            "category_id": category_id,
        },
    )
    return resp.json()["id"]


def _fill_cart(client, user_token, product_id, quantity=2):
    client.post(
        "/api/v1/cart/",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"product_id": product_id, "quantity": quantity},
    )


def _place_order(client, user_token):
    return client.post(
        "/api/v1/orders/create",
        headers={"Authorization": f"Bearer {user_token}"},
    )


def test_create_order_from_cart(client):
    admin_token = _register_and_login(client, "ord_admin", "ord_admin@test.com", "admin")
    user_token  = _register_and_login(client, "ord_buyer", "ord_buyer@test.com", "user")

    cat_id  = _create_category(client, admin_token, "OrderCat")
    prod_id = _create_product(client, admin_token, cat_id, "OrderProd")
    _fill_cart(client, user_token, prod_id)

    response = _place_order(client, user_token)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert data["total_price"] > 0


def test_create_order_with_empty_cart(client):
    """Placing an order when the cart is empty must return 404."""
    user_token = _register_and_login(client, "empty_buyer", "empty_buyer@test.com")
    response = _place_order(client, user_token)
    assert response.status_code == 404


def test_order_unauthorized(client):
    """Creating an order without a token must return 401."""
    response = client.post("/api/v1/orders/create")
    assert response.status_code == 401


def test_get_my_orders(client):
    admin_token = _register_and_login(client, "my_ord_admin", "my_ord_admin@test.com", "admin")
    user_token  = _register_and_login(client, "my_ord_buyer", "my_ord_buyer@test.com", "user")

    cat_id  = _create_category(client, admin_token, "MyOrderCat")
    prod_id = _create_product(client, admin_token, cat_id, "MyOrderProd")
    _fill_cart(client, user_token, prod_id)
    _place_order(client, user_token)

    response = client.get(
        "/api/v1/orders/get/my_orders",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code in [200, 404]


def test_get_all_orders_as_admin(client):
    admin_token = _register_and_login(client, "all_ord_admin", "all_ord_admin@test.com", "admin")
    response = client.get(
        "/api/v1/orders/get_all_orders",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code in [200, 404]


def test_get_all_orders_as_user_forbidden(client):
    user_token = _register_and_login(client, "all_ord_user", "all_ord_user@test.com", "user")
    response = client.get(
        "/api/v1/orders/get_all_orders",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_get_all_orders_unauthorized(client):
    response = client.get("/api/v1/orders/get_all_orders")
    assert response.status_code in [401, 403]


def test_cancel_pending_order(client):
    admin_token = _register_and_login(client, "cancel_admin", "cancel_admin@test.com", "admin")
    user_token  = _register_and_login(client, "cancel_buyer", "cancel_buyer@test.com", "user")

    cat_id  = _create_category(client, admin_token, "CancelCat")
    prod_id = _create_product(client, admin_token, cat_id, "CancelProd")
    _fill_cart(client, user_token, prod_id)
    order_resp = _place_order(client, user_token)
    order_id = order_resp.json()["id"]

    response = client.delete(
        f"/api/v1/orders/cancel/{order_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 200


def test_cancel_nonexistent_order(client):
    user_token = _register_and_login(client, "cancel_ghost", "cancel_ghost@test.com", "user")
    response = client.delete(
        "/api/v1/orders/cancel/999999",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404



def test_ship_order_as_admin(client):
    admin_token = _register_and_login(client, "ship_admin", "ship_admin@test.com", "admin")
    user_token  = _register_and_login(client, "ship_buyer", "ship_buyer@test.com", "user")

    cat_id  = _create_category(client, admin_token, "ShipCat")
    prod_id = _create_product(client, admin_token, cat_id, "ShipProd")
    _fill_cart(client, user_token, prod_id)
    order_resp = _place_order(client, user_token)
    order_id = order_resp.json()["id"]

    response = client.put(
        f"/api/v1/orders/put/ship/{order_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200


def test_ship_order_as_user_forbidden(client):
    admin_token = _register_and_login(client, "ship_admin2", "ship_admin2@test.com", "admin")
    user_token  = _register_and_login(client, "ship_buyer2", "ship_buyer2@test.com", "user")

    cat_id  = _create_category(client, admin_token, "ShipCat2")
    prod_id = _create_product(client, admin_token, cat_id, "ShipProd2")
    _fill_cart(client, user_token, prod_id)
    order_resp = _place_order(client, user_token)
    order_id = order_resp.json()["id"]

    response = client.put(
        f"/api/v1/orders/put/ship/{order_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 403


def test_cancel_already_shipped_order(client):
    """Cancelling a shipped order must be rejected (invalid state transition)."""
    admin_token = _register_and_login(client, "state_admin", "state_admin@test.com", "admin")
    user_token  = _register_and_login(client, "state_buyer", "state_buyer@test.com", "user")

    cat_id  = _create_category(client, admin_token, "StateCat")
    prod_id = _create_product(client, admin_token, cat_id, "StateProd")
    _fill_cart(client, user_token, prod_id)
    order_resp = _place_order(client, user_token)
    order_id = order_resp.json()["id"]

    client.put(
        f"/api/v1/orders/put/ship/{order_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )

    response = client.delete(
        f"/api/v1/orders/cancel/{order_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    assert response.status_code == 404 