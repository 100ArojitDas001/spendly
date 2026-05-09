"""Route-level integration tests for GET /profile."""


def test_profile_unauthenticated_redirects(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_authenticated_returns_200(auth_client):
    response = auth_client.get("/profile")
    assert response.status_code == 200


def test_profile_shows_user_name(auth_client):
    response = auth_client.get("/profile")
    assert b"Demo User" in response.data


def test_profile_shows_user_email(auth_client):
    response = auth_client.get("/profile")
    assert b"demo@spendly.com" in response.data


def test_profile_shows_rupee_symbol(auth_client):
    response = auth_client.get("/profile")
    assert "₹".encode() in response.data


def test_profile_total_spent(auth_client):
    response = auth_client.get("/profile")
    assert b"338.25" in response.data


def test_profile_transaction_count(auth_client):
    response = auth_client.get("/profile")
    assert b"8" in response.data


def test_profile_top_category(auth_client):
    response = auth_client.get("/profile")
    assert b"Bills" in response.data


def test_profile_transaction_order(auth_client):
    """May 08 must appear before May 01 in the rendered HTML."""
    response = auth_client.get("/profile")
    html = response.data.decode()
    assert html.index("May 08") < html.index("May 01")


def test_profile_seven_categories(auth_client):
    response = auth_client.get("/profile")
    html = response.data.decode()
    for category in ("Bills", "Shopping", "Transport", "Health", "Entertainment", "Food", "Other"):
        assert category in html
