import pytest
import database.db as _db
from app import app as flask_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    db_file = tmp_path / "test.db"
    monkeypatch.setattr(_db, "DB_PATH", str(db_file))
    with flask_app.app_context():
        _db.init_db()
        _db.seed_db()
    flask_app.config["TESTING"] = True
    flask_app.config["SECRET_KEY"] = "test-secret"
    yield flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post("/login", data={"email": "demo@spendly.com", "password": "demo123"})
    return client
