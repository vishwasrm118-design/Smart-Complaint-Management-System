import sqlite3

import pytest

import app as complaint_app


@pytest.fixture
def client(tmp_path):
    complaint_app.app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        DATABASE=str(tmp_path / "test_complaints.db"),
    )

    with complaint_app.app.test_client() as test_client:
        yield test_client


def test_registration_success(client):
    response = client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "test@example.com",
            "password": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Registration successful" in response.data

    with complaint_app.app.app_context():
        db = complaint_app.get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?",
            ("test@example.com",),
        ).fetchone()

    assert user is not None
    assert user["password_hash"] != "password123"


def test_registration_rejects_missing_fields(client):
    response = client.post(
        "/register",
        data={"name": "", "email": "", "password": ""},
    )

    assert response.status_code == 200
    assert b"All fields are required" in response.data


def test_registration_rejects_short_password(client):
    response = client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "short@example.com",
            "password": "123",
        },
    )

    assert response.status_code == 200
    assert b"at least 8 characters" in response.data


def test_registration_rejects_duplicate_email(client):
    client.post(
        "/register",
        data={
            "name": "First User",
            "email": "same@example.com",
            "password": "password123",
        },
    )

    response = client.post(
        "/register",
        data={
            "name": "Second User",
            "email": "same@example.com",
            "password": "password456",
        },
    )

    assert response.status_code == 200
    assert b"already exists" in response.data


def test_login_success(client):
    client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "login@example.com",
            "password": "password123",
        },
    )

    response = client.post(
        "/login",
        data={
            "email": "login@example.com",
            "password": "password123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"My Complaints" in response.data


def test_login_rejects_invalid_password(client):
    client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "login@example.com",
            "password": "password123",
        },
    )

    response = client.post(
        "/login",
        data={
            "email": "login@example.com",
            "password": "wrongpassword",
        },
    )

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_dashboard_requires_login(client):
    response = client.get("/")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_logout_clears_session(client):
    client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "logout@example.com",
            "password": "password123",
        },
    )
    client.post(
        "/login",
        data={
            "email": "logout@example.com",
            "password": "password123",
        },
    )

    response = client.get("/logout", follow_redirects=True)

    assert response.status_code == 200
    assert b"Log In" in response.data

    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]