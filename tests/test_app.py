
import pytest
import app as complaint_app


@pytest.fixture
def client(tmp_path):
    complaint_app.app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        DATABASE=str(tmp_path / "test_complaints.db"),
        ADMIN_EMAILS="",
    )

    with complaint_app.app.test_client() as test_client:
        yield test_client


def create_account(client, email):
    response = client.post(
        "/register",
        data={
            "name": "Test User",
            "email": email,
            "password": "password123",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200


def login_as(client, email):
    return client.post(
        "/login",
        data={"email": email, "password": "password123"},
        follow_redirects=True,
    )


def register_and_login(client, email="test@example.com"):
    create_account(client, email)
    return login_as(client, email)


def lodge_test_complaint(client, title="Status test complaint"):
    return client.post(
        "/complaints/new",
        data={
            "title": title,
            "category": "Infrastructure",
            "description": "Testing status management.",
        },
        follow_redirects=False,
    )


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
        user = complaint_app.get_db().execute(
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
    create_account(client, "same@example.com")
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
    create_account(client, "login@example.com")
    response = login_as(client, "login@example.com")
    assert response.status_code == 200
    assert b"My Complaints" in response.data


def test_login_rejects_invalid_password(client):
    create_account(client, "login@example.com")
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
    register_and_login(client, "logout@example.com")
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200

    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


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


def test_admin_can_update_status_and_owner_sees_latest_status(client):
    complaint_app.app.config["ADMIN_EMAILS"] = "admin@example.com"

    register_and_login(client, "owner@example.com")
    response = lodge_test_complaint(client)
    assert response.status_code == 302
    complaint_id = int(response.headers["Location"].rstrip("/").split("/")[-1])

    client.get("/logout")
    register_and_login(client, "admin@example.com")

    response = client.post(
        f"/admin/complaints/{complaint_id}/status",
        data={"status": "In Progress"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"status updated to In Progress" in response.data

    with complaint_app.app.app_context():
        row = complaint_app.get_db().execute(
            "SELECT status FROM complaints WHERE id = ?",
            (complaint_id,),
        ).fetchone()
    assert row["status"] == "In Progress"

    client.get("/logout")
    login_as(client, "owner@example.com")
    response = client.get(f"/complaints/{complaint_id}")
    assert response.status_code == 200
    assert b"In Progress" in response.data


def test_invalid_status_value_is_rejected(client):
    complaint_app.app.config["ADMIN_EMAILS"] = "admin@example.com"
    register_and_login(client, "owner@example.com")
    lodge_test_complaint(client)

    client.get("/logout")
    register_and_login(client, "admin@example.com")

    response = client.post(
        "/admin/complaints/1/status",
        data={"status": "Completed"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid complaint status." in response.data

    with complaint_app.app.app_context():
        row = complaint_app.get_db().execute(
            "SELECT status FROM complaints WHERE id = 1"
        ).fetchone()
    assert row["status"] == "Submitted"


def test_unauthenticated_user_cannot_update_status(client):
    response = client.post(
        "/admin/complaints/1/status",
        data={"status": "Resolved"},
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_regular_user_cannot_access_admin_status_management(client):
    register_and_login(client, "regular@example.com")
    response = client.get("/admin/complaints")
    assert response.status_code == 403


def test_regular_user_cannot_update_another_users_complaint(client):
    complaint_app.app.config["ADMIN_EMAILS"] = "admin@example.com"
    register_and_login(client, "owner@example.com")
    lodge_test_complaint(client)

    client.get("/logout")
    register_and_login(client, "other@example.com")

    response = client.post(
        "/admin/complaints/1/status",
        data={"status": "Rejected"},
    )
    assert response.status_code == 403

    with complaint_app.app.app_context():
        row = complaint_app.get_db().execute(
            "SELECT status FROM complaints WHERE id = 1"
        ).fetchone()
    assert row["status"] == "Submitted"


def test_status_update_returns_not_found_for_missing_complaint(client):
    complaint_app.app.config["ADMIN_EMAILS"] = "admin@example.com"
    register_and_login(client, "admin@example.com")

    response = client.post(
        "/admin/complaints/999/status",
        data={"status": "Resolved"},
    )
    assert response.status_code == 404


def test_regular_user_cannot_change_own_complaint_status(client):
    register_and_login(client, "owner@example.com")
    lodge_test_complaint(client)

    response = client.post(
        "/admin/complaints/1/status",
        data={"status": "Resolved"},
    )
    assert response.status_code == 403

    with complaint_app.app.app_context():
        row = complaint_app.get_db().execute(
            "SELECT status FROM complaints WHERE id = 1"
        ).fetchone()
    assert row["status"] == "Submitted"


def test_complaint_submission_and_tracking_remain_available(client):
    register_and_login(client, "reporter@example.com")
    response = lodge_test_complaint(client, "Leaking classroom pipe")
    assert response.status_code == 302

    response = client.get(response.headers["Location"])
    assert response.status_code == 200
    assert b"Leaking classroom pipe" in response.data
    assert b"Submitted" in response.data


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
    assert b"Private complaint" not in response.data


def test_complaint_history_requires_login(client):
    response = client.get("/complaint-history")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_user_can_view_own_complaint_history(client):
    register_and_login(client, "history@example.com")

    lodge_test_complaint(client, "Broken classroom fan")
    lodge_test_complaint(client, "Water leakage")

    response = client.get("/complaint-history")

    assert response.status_code == 200
    assert b"My Complaint History" in response.data
    assert b"Broken classroom fan" in response.data
    assert b"Water leakage" in response.data
    assert b"Infrastructure" in response.data


def test_user_cannot_view_another_users_complaint_history(client):
    register_and_login(client, "first@example.com")

    lodge_test_complaint(client, "Private complaint")

    client.get("/logout")
    register_and_login(client, "second@example.com")

    response = client.get("/complaint-history")

    assert response.status_code == 200
    assert b"Private complaint" not in response.data
    assert b"Testing status management." not in response.data


def test_empty_complaint_history(client):
    register_and_login(client, "empty@example.com")

    response = client.get("/complaint-history")

    assert response.status_code == 200
    assert b"No complaint history found" in response.data

def test_admin_dashboard_requires_login(client):
    response = client.get("/admin/dashboard")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_regular_user_cannot_access_admin_dashboard(client):
    register_and_login(client, "regular@example.com")

    response = client.get("/admin/dashboard")

    assert response.status_code == 403


def test_admin_dashboard_shows_correct_statistics(client):
    # Configure this email as an administrator.
    complaint_app.app.config["ADMIN_EMAILS"] = "admin@example.com"

    # Create and log in the administrator.
    create_account(client, "admin@example.com")
    login_as(client, "admin@example.com")

    # Create a regular user who will submit complaints.
    client.get("/logout")
    create_account(client, "student@example.com")
    login_as(client, "student@example.com")

    # Submit two complaints.
    client.post(
        "/complaints/new",
        data={
            "title": "Broken classroom fan",
            "category": "Infrastructure",
            "description": "The fan is not working.",
        },
    )

    client.post(
        "/complaints/new",
        data={
           "title": "Library computer issue",
"category": "Electrical",
"description": "The computer will not start.",
        },
    )

    # Log in as the administrator and open the dashboard.
    client.get("/logout")
    login_as(client, "admin@example.com")

    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    assert b"Admin Dashboard" in response.data
    assert b"Total Complaints" in response.data
    assert b"Total Users" in response.data
    assert b"Broken classroom fan" in response.data
    assert b"Library computer issue" in response.data

    # Verify the statistics directly in the test database.
    with complaint_app.app.app_context():
        db = complaint_app.get_db()

        assert db.execute(
            "SELECT COUNT(*) FROM complaints"
        ).fetchone()[0] == 2

        assert db.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()[0] == 2


def test_admin_dashboard_handles_empty_database(client):
    complaint_app.app.config["ADMIN_EMAILS"] = "admin@example.com"

    create_account(client, "admin@example.com")
    login_as(client, "admin@example.com")

    response = client.get("/admin/dashboard")

    assert response.status_code == 200
    assert b"Admin Dashboard" in response.data
    assert b"No complaints have been submitted yet." in response.data
    assert b"No complaint categories to display yet." in response.data



def test_user_can_search_complaint_history_by_title(client):
    register_and_login(client, "searchuser@example.com")
    lodge_test_complaint(client, "Broken classroom fan")
    lodge_test_complaint(client, "Water leakage")

    response = client.get(
        "/complaint-history?q=Broken+classroom+fan"
    )

    assert response.status_code == 200
    assert b"Broken classroom fan" in response.data
    assert b"Water leakage" not in response.data


def test_user_can_filter_complaint_history_by_category(client):
    register_and_login(client, "categoryuser@example.com")
    lodge_test_complaint(client, "Broken classroom fan")

    client.post(
        "/complaints/new",
        data={
            "title": "Electrical wiring issue",
            "category": "Electrical",
            "description": "Wiring needs repair.",
        },
    )

    response = client.get(
        "/complaint-history?category=Electrical"
    )

    assert response.status_code == 200
    assert b"Electrical wiring issue" in response.data
    assert b"Broken classroom fan" not in response.data


def test_user_can_filter_complaint_history_by_status(client):
    register_and_login(client, "statusfilter@example.com")
    lodge_test_complaint(client, "Complaint to resolve")
    lodge_test_complaint(client, "Complaint still submitted")

    with complaint_app.app.app_context():
        complaint_app.get_db().execute(
            "UPDATE complaints SET status = ? WHERE title = ?",
            ("Resolved", "Complaint to resolve"),
        )
        complaint_app.get_db().commit()

    response = client.get("/complaint-history?status=Resolved")

    assert response.status_code == 200
    assert b"Complaint to resolve" in response.data
    assert b"Complaint still submitted" not in response.data


def test_user_can_combine_complaint_history_filters(client):
    register_and_login(client, "combinedfilter@example.com")

    client.post(
        "/complaints/new",
        data={
            "title": "Electrical fan repair",
            "category": "Electrical",
            "description": "Fan is broken.",
        },
    )
    client.post(
        "/complaints/new",
        data={
            "title": "Electrical light repair",
            "category": "Electrical",
            "description": "Light is broken.",
        },
    )

    response = client.get(
        "/complaint-history?q=fan&category=Electrical"
    )

    assert response.status_code == 200
    assert b"Electrical fan repair" in response.data
    assert b"Electrical light repair" not in response.data


def test_user_search_does_not_show_other_users_complaints(client):
    register_and_login(client, "firstsearch@example.com")
    lodge_test_complaint(client, "My private complaint")

    client.get("/logout")
    register_and_login(client, "secondsearch@example.com")

    response = client.get(
        "/complaint-history?q=private"
    )

    assert response.status_code == 200
    assert b"My private complaint" not in response.data


def test_admin_can_search_complaints_by_description(client):
    complaint_app.app.config["ADMIN_EMAILS"] = "admin@example.com"

    register_and_login(client, "reporter@example.com")
    client.post(
        "/complaints/new",
        data={
            "title": "Classroom problem",
            "category": "Infrastructure",
            "description": "Projector screen is damaged.",
        },
    )

    client.get("/logout")
    register_and_login(client, "admin@example.com")

    response = client.get(
        "/admin/complaints?q=Projector+screen"
    )

    assert response.status_code == 200
    assert b"Classroom problem" in response.data


def test_admin_can_combine_status_and_category_filters(client):
    complaint_app.app.config["ADMIN_EMAILS"] = "admin@example.com"

    register_and_login(client, "reporter@example.com")

    client.post(
        "/complaints/new",
        data={
            "title": "Electrical issue resolved",
            "category": "Electrical",
            "description": "First electrical complaint.",
        },
    )
    client.post(
        "/complaints/new",
        data={
            "title": "Electrical issue submitted",
            "category": "Electrical",
            "description": "Second electrical complaint.",
        },
    )

    with complaint_app.app.app_context():
        complaint_app.get_db().execute(
            "UPDATE complaints SET status = ? WHERE title = ?",
            ("Resolved", "Electrical issue resolved"),
        )
        complaint_app.get_db().commit()

    client.get("/logout")
    register_and_login(client, "admin@example.com")

    response = client.get(
        "/admin/complaints?status=Resolved&category=Electrical"
    )

    assert response.status_code == 200
    assert b"Electrical issue resolved" in response.data
    assert b"Electrical issue submitted" not in response.data



def test_admin_search_with_no_matches_shows_empty_state(client):
    complaint_app.app.config["ADMIN_EMAILS"] = "admin@example.com"
    register_and_login(client, "admin@example.com")

    response = client.get(
        "/admin/complaints?q=NoSuchComplaint12345"
    )

    assert response.status_code == 200
    assert b"No complaints match your search." in response.data
