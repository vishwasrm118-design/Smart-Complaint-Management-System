import pytest
from app import app as flask_app


@pytest.fixture
def client(tmp_path):
    database_path = tmp_path / "test_complaints.db"
    flask_app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        DATABASE=str(database_path),
    )

    with flask_app.test_client() as test_client:
        yield test_client


def register_and_login(client, email="test@example.com"):
    client.post(
        "/register",
        data={
            "name": "Test User",
            "email": email,
            "password": "TestPassword123",
        },
        follow_redirects=True,
    )
    return client.post(
        "/login",
        data={
            "email": email,
            "password": "TestPassword123",
        },
        follow_redirects=True,
    )


def test_lodge_complaint_successfully(client):
    register_and_login(client)

    response = client.post(
        "/complaints/new",
        data={
            "title": "Broken Classroom Fan",
            "category": "Infrastructure",
            "description": "The fan is not working.",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Broken Classroom Fan" in response.data
    assert b"Infrastructure" in response.data
    assert b"The fan is not working." in response.data
    assert b"Submitted" in response.data


def test_lodge_complaint_requires_login(client):
    response = client.get("/complaints/new")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_missing_title_is_rejected(client):
    register_and_login(client)

    response = client.post(
        "/complaints/new",
        data={
            "title": "",
            "category": "Infrastructure",
            "description": "A description.",
        },
    )

    assert response.status_code == 200
    assert b"Title, category, and description are required." in response.data


def test_invalid_category_is_rejected(client):
    register_and_login(client)

    response = client.post(
        "/complaints/new",
        data={
            "title": "Test complaint",
            "category": "InvalidCategory",
            "description": "A description.",
        },
    )

    assert response.status_code == 200
    assert b"Please select a valid complaint category." in response.data


def test_user_cannot_track_another_users_complaint(client):
    register_and_login(client, "first@example.com")

    client.post(
        "/complaints/new",
        data={
            "title": "Private complaint",
            "category": "Electrical",
            "description": "Private details.",
        },
    )

    client.get("/logout")
    register_and_login(client, "second@example.com")

    response = client.get("/complaints/1", follow_redirects=True)

    assert response.status_code == 200
    assert b"Complaint not found." in response.data
    assert b"Private details." not in response.data

