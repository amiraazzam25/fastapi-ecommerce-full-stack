import pytest



def test_register_success(client):
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": "authuser",
            "email": "authuser@test.com",
            "password": "securePass1",
            "role": "user",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "authuser@test.com"
    assert data["username"] == "authuser"
    assert "password" not in data 


def test_register_duplicate_email(client):
    """Registering with an already-used e-mail must return 409."""
    client.post(
        "/api/v1/users/register",
        json={
            "username": "dupemailuser",
            "email": "authuser@test.com", 
            "password": "securePass1",
            "role": "user",
        },
    )
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": "dupemailuser",
            "email": "authuser@test.com",
            "password": "securePass1",
            "role": "user",
        },
    )
    assert response.status_code == 409


def test_register_duplicate_username(client):
    """Registering with an already-used username must return 409."""
    client.post(
        "/api/v1/users/register",
        json={
            "username": "authuser",         
            "email": "unique_for_dup@test.com",
            "password": "securePass1",
            "role": "user",
        },
    )
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": "authuser",
            "email": "unique_for_dup2@test.com",
            "password": "securePass1",
            "role": "user",
        },
    )
    assert response.status_code == 409


def test_register_invalid_email_format(client):
    """Bad e-mail format must be rejected (422 Unprocessable Entity)."""
    response = client.post(
        "/api/v1/users/register",
        json={
            "username": "bademailuser",
            "email": "not-an-email",
            "password": "securePass1",
            "role": "user",
        },
    )
    assert response.status_code == 422



def test_login_success(client):
    response = client.post(
        "/api/v1/users/login",
        data={"username": "authuser@test.com", "password": "securePass1"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    response = client.post(
        "/api/v1/users/login",
        data={"username": "authuser@test.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_login_nonexistent_user(client):
    response = client.post(
        "/api/v1/users/login",
        data={"username": "nobody@test.com", "password": "irrelevant"},
    )
    assert response.status_code == 401


def test_get_current_user_with_valid_token(client):
    """A valid token must allow access to /me."""
    login = client.post(
        "/api/v1/users/login",
        data={"username": "authuser@test.com", "password": "securePass1"},
    )
    token = login.json()["access_token"]

    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["email"] == "authuser@test.com"


def test_get_current_user_without_token(client):
    """Missing token must return 401."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_get_current_user_with_invalid_token(client):
    """Tampered / invalid token must return 401."""
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer totally.fake.token"},
    )
    assert response.status_code == 401



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


def test_admin_endpoint_blocked_for_regular_user(client):
    """A regular user must NOT be able to list all users (admin only)."""
    token = _register_and_login(client, "regularuser1", "regular1@test.com", "user")
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_admin_endpoint_accessible_for_admin(client):
    """An admin user must be able to list all users."""
    token = _register_and_login(client, "adminuser1", "admin1@test.com", "admin")
    response = client.get(
        "/api/v1/users/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_edit_own_profile(client):
    """An authenticated user can edit their own profile."""
    token = _register_and_login(client, "editme", "editme@test.com", "user")
    response = client.put(
        "/api/v1/users/edit",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "editme_updated"},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "editme_updated"
