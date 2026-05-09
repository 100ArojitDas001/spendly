"""Integration tests for GET/POST /login and GET /logout."""


def test_login_get_returns_200(client):
    response = client.get("/login")
    assert response.status_code == 200


def test_login_page_has_form(client):
    response = client.get("/login")
    assert b"<form" in response.data


def test_login_valid_credentials_redirects_to_profile(client):
    response = client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "demo123"},
    )
    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


def test_login_sets_session(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    response = client.get("/profile")
    assert response.status_code == 200


def test_login_wrong_password_returns_200(client):
    response = client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "wrongpassword"},
    )
    assert response.status_code == 200


def test_login_wrong_password_shows_error(client):
    response = client.post(
        "/login",
        data={"email": "demo@spendly.com", "password": "wrongpassword"},
    )
    assert b"Invalid email or password" in response.data


def test_login_unknown_email_shows_error(client):
    response = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "anything"},
    )
    assert b"Invalid email or password" in response.data


def test_login_unknown_email_returns_200(client):
    response = client.post(
        "/login",
        data={"email": "nobody@example.com", "password": "anything"},
    )
    assert response.status_code == 200


def test_logout_redirects_to_login(auth_client):
    response = auth_client.get("/logout")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logout_clears_session(auth_client):
    auth_client.get("/logout")
    response = auth_client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
