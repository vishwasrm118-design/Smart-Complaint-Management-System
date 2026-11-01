
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
def _create_feedback_test_complaint(client, email, title, status="Resolved"):
    client.post(
        "/complaints/new",
        data={
            "title": title,
            "category": "Electrical",
            "description": "Test complaint for feedback.",
        },
    )

    with complaint_app.app.app_context():
        db = complaint_app.get_db()

        user = db.execute(
            "SELECT id FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()

        complaint = db.execute(
            """
            SELECT id FROM complaints
            WHERE user_id = ? AND title = ?
            ORDER BY id DESC LIMIT 1
            """,
            (user["id"], title),
        ).fetchone()

        db.execute(
            "UPDATE complaints SET status = ? WHERE id = ?",
            (status, complaint["id"]),
        )
        db.commit()

        return complaint["id"]
def test_user_can_open_feedback_form_for_resolved_complaint(client):
    email = "feedbackform@example.com"
    register_and_login(client, email)

    complaint_id = _create_feedback_test_complaint(
        client, email, "Resolved feedback form complaint"
    )

    response = client.get(f"/feedback/{complaint_id}")

    assert response.status_code == 200
    assert b"Submit Feedback" in response.data


def test_user_can_submit_feedback(client):
    email = "feedbacksubmit@example.com"
    register_and_login(client, email)

    complaint_id = _create_feedback_test_complaint(
        client, email, "Feedback submission complaint"
    )

    response = client.post(
        f"/feedback/{complaint_id}",
        data={"rating": "5", "comments": "Excellent service"},
    )

    assert response.status_code == 302
    assert "/feedback/history" in response.location

    with complaint_app.app.app_context():
        feedback = complaint_app.get_db().execute(
            """
            SELECT rating, comments FROM feedback
            WHERE complaint_id = ?
            """,
            (complaint_id,),
        ).fetchone()

    assert feedback["rating"] == 5
    assert feedback["comments"] == "Excellent service"


def test_feedback_rejects_invalid_ratings(client):
    email = "invalidrating@example.com"
    register_and_login(client, email)

    complaint_id = _create_feedback_test_complaint(
        client, email, "Invalid rating complaint"
    )

    for rating in ["0", "6", "abc", ""]:
        response = client.post(
            f"/feedback/{complaint_id}",
            data={"rating": rating, "comments": ""},
        )

        assert response.status_code == 200
        assert b"Please select a rating from 1 to 5." in response.data

    with complaint_app.app.app_context():
        count = complaint_app.get_db().execute(
            "SELECT COUNT(*) FROM feedback WHERE complaint_id = ?",
            (complaint_id,),
        ).fetchone()[0]

    assert count == 0


def test_feedback_rejects_unresolved_complaint(client):
    email = "unresolved@example.com"
    register_and_login(client, email)

    complaint_id = _create_feedback_test_complaint(
        client, email, "Unresolved complaint", status="Submitted"
    )

    response = client.post(
        f"/feedback/{complaint_id}",
        data={"rating": "4", "comments": "Test"},
    )

    assert response.status_code == 302
    assert "/complaint-history" in response.location

    with complaint_app.app.app_context():
        count = complaint_app.get_db().execute(
            "SELECT COUNT(*) FROM feedback WHERE complaint_id = ?",
            (complaint_id,),
        ).fetchone()[0]

    assert count == 0


def test_user_cannot_submit_feedback_for_another_users_complaint(client):
    first_email = "ownerfeedback@example.com"
    register_and_login(client, first_email)

    complaint_id = _create_feedback_test_complaint(
        client, first_email, "Another user's complaint"
    )

    client.get("/logout")
    register_and_login(client, "otherfeedback@example.com")

    response = client.post(
        f"/feedback/{complaint_id}",
        data={"rating": "5", "comments": "Unauthorized"},
    )

    assert response.status_code == 404


def test_user_cannot_submit_duplicate_feedback(client):
    email = "duplicatefeedback@example.com"
    register_and_login(client, email)

    complaint_id = _create_feedback_test_complaint(
        client, email, "Duplicate feedback complaint"
    )

    data = {"rating": "4", "comments": "Good service"}

    first_response = client.post(f"/feedback/{complaint_id}", data=data)
    second_response = client.post(f"/feedback/{complaint_id}", data=data)

    assert first_response.status_code == 302
    assert second_response.status_code == 302

    with complaint_app.app.app_context():
        count = complaint_app.get_db().execute(
            """
            SELECT COUNT(*) FROM feedback
            WHERE complaint_id = ?
            """,
            (complaint_id,),
        ).fetchone()[0]

    assert count == 1


def test_feedback_history_shows_only_current_users_feedback(client):
    first_email = "privatefeedback@example.com"
    register_and_login(client, first_email)

    first_id = _create_feedback_test_complaint(
        client, first_email, "First user's complaint"
    )

    client.post(
        f"/feedback/{first_id}",
        data={"rating": "5", "comments": "Private feedback comment"},
    )

    client.get("/logout")
    register_and_login(client, "secondfeedback@example.com")

    response = client.get("/feedback/history")

    assert response.status_code == 200
    assert b"Private feedback comment" not in response.data


def test_feedback_history_requires_login(client):
    response = client.get("/feedback/history")

    assert response.status_code == 302
    assert "/login" in response.location


def test_complaint_history_feedback_button_matches_status(client):
    email = "feedbackbutton@example.com"
    register_and_login(client, email)

    _create_feedback_test_complaint(
        client, email, "Resolved button complaint", status="Resolved"
    )
    _create_feedback_test_complaint(
        client, email, "Submitted button complaint", status="Submitted"
    )

    resolved_response = client.get(
        "/complaint-history?status=Resolved"
    )
    submitted_response = client.get(
        "/complaint-history?status=Submitted"
    )

    assert b"Give Feedback" in resolved_response.data
    assert b"Submitted button complaint" in submitted_response.data
    assert b"Give Feedback" not in submitted_response.data


def test_complaint_history_shows_feedback_submitted(client):
    email = "feedbacksubmitted@example.com"
    register_and_login(client, email)

    complaint_id = _create_feedback_test_complaint(
        client, email, "Already rated complaint"
    )

    client.post(
        f"/feedback/{complaint_id}",
        data={"rating": "5", "comments": "Thank you"},
    )

    response = client.get("/complaint-history?status=Resolved")

    assert response.status_code == 200
    assert b"Feedback Submitted" in response.data
    assert b"Give Feedback" not in response.data


# User notification feature tests

def create_owner_complaint_and_admin(client):
    complaint_app.app.config["ADMIN_EMAILS"] = "admin@example.com"
    register_and_login(client, "notification-owner@example.com")
    response = lodge_test_complaint(client, "Notification test complaint")
    complaint_id = int(response.headers["Location"].rstrip("/").split("/")[-1])
    client.get("/logout")
    register_and_login(client, "admin@example.com")
    return complaint_id


def test_notification_is_created_when_complaint_status_changes(client):
    complaint_id = create_owner_complaint_and_admin(client)
    response = client.post(
        f"/admin/complaints/{complaint_id}/status",
        data={"status": "In Progress"},
    )
    assert response.status_code == 302
    with complaint_app.app.app_context():
        row = complaint_app.get_db().execute(
            "SELECT * FROM notifications WHERE complaint_id = ?", (complaint_id,)
        ).fetchone()
    assert row is not None
    assert row["message"] == f"Your complaint #{complaint_id} is now In Progress."
    assert row["is_read"] == 0


def test_correct_complaint_owner_receives_notification(client):
    complaint_id = create_owner_complaint_and_admin(client)
    client.post(f"/admin/complaints/{complaint_id}/status", data={"status": "In Progress"})
    with complaint_app.app.app_context():
        owner = complaint_app.get_db().execute(
            "SELECT id FROM users WHERE email = ?", ("notification-owner@example.com",)
        ).fetchone()
        notification = complaint_app.get_db().execute(
            "SELECT user_id FROM notifications WHERE complaint_id = ?", (complaint_id,)
        ).fetchone()
    assert notification["user_id"] == owner["id"]


def test_notification_is_not_sent_to_unrelated_users_or_admin(client):
    complaint_id = create_owner_complaint_and_admin(client)
    create_account(client, "unrelated@example.com")
    client.post(f"/admin/complaints/{complaint_id}/status", data={"status": "In Progress"})
    with complaint_app.app.app_context():
        db = complaint_app.get_db()
        unrelated = db.execute("SELECT id FROM users WHERE email = ?", ("unrelated@example.com",)).fetchone()["id"]
        admin = db.execute("SELECT id FROM users WHERE email = ?", ("admin@example.com",)).fetchone()["id"]
        recipients = [r["user_id"] for r in db.execute("SELECT user_id FROM notifications").fetchall()]
    assert unrelated not in recipients
    assert admin not in recipients


def test_user_can_view_only_their_notifications(client):
    complaint_id = create_owner_complaint_and_admin(client)
    client.post(f"/admin/complaints/{complaint_id}/status", data={"status": "In Progress"})
    client.get("/logout")
    login_as(client, "notification-owner@example.com")
    response = client.get("/notifications")
    assert response.status_code == 200
    assert b"My Notifications" in response.data
    assert b"Notification test complaint" not in response.data  # message is status-based
    assert f"#{complaint_id}".encode() in response.data


def test_user_cannot_view_another_users_notifications(client):
    complaint_id = create_owner_complaint_and_admin(client)
    client.post(f"/admin/complaints/{complaint_id}/status", data={"status": "In Progress"})
    client.get("/logout")
    register_and_login(client, "intruder@example.com")
    response = client.get("/notifications")
    assert response.status_code == 200
    assert f"#{complaint_id}".encode() not in response.data
    assert b"You have no notifications yet." in response.data


def test_user_can_mark_own_notification_as_read(client):
    complaint_id = create_owner_complaint_and_admin(client)
    client.post(f"/admin/complaints/{complaint_id}/status", data={"status": "In Progress"})
    with complaint_app.app.app_context():
        notification_id = complaint_app.get_db().execute(
            "SELECT id FROM notifications WHERE complaint_id = ?", (complaint_id,)
        ).fetchone()["id"]
    client.get("/logout")
    login_as(client, "notification-owner@example.com")
    response = client.post(f"/notifications/{notification_id}/read")
    assert response.status_code == 302
    with complaint_app.app.app_context():
        row = complaint_app.get_db().execute(
            "SELECT is_read FROM notifications WHERE id = ?", (notification_id,)
        ).fetchone()
    assert row["is_read"] == 1


def test_user_cannot_mark_another_users_notification_as_read(client):
    complaint_id = create_owner_complaint_and_admin(client)
    client.post(f"/admin/complaints/{complaint_id}/status", data={"status": "In Progress"})
    with complaint_app.app.app_context():
        notification_id = complaint_app.get_db().execute(
            "SELECT id FROM notifications WHERE complaint_id = ?", (complaint_id,)
        ).fetchone()["id"]
    client.get("/logout")
    register_and_login(client, "intruder@example.com")
    response = client.post(f"/notifications/{notification_id}/read")
    assert response.status_code == 404
    with complaint_app.app.app_context():
        row = complaint_app.get_db().execute(
            "SELECT is_read FROM notifications WHERE id = ?", (notification_id,)
        ).fetchone()
    assert row["is_read"] == 0


def test_mark_all_notifications_as_read(client):
    complaint_id = create_owner_complaint_and_admin(client)
    client.post(f"/admin/complaints/{complaint_id}/status", data={"status": "In Progress"})
    client.get("/logout")
    login_as(client, "notification-owner@example.com")
    response = client.post("/notifications/mark-all-read")
    assert response.status_code == 302
    with complaint_app.app.app_context():
        unread = complaint_app.get_db().execute(
            "SELECT COUNT(*) FROM notifications WHERE is_read = 0"
        ).fetchone()[0]
    assert unread == 0


def test_notification_routes_require_login(client):
    assert client.get("/notifications").status_code == 302
    assert client.post("/notifications/1/read").status_code == 302
    assert client.post("/notifications/mark-all-read").status_code == 302


def test_empty_notification_list_is_handled(client):
    register_and_login(client, "empty-notifications@example.com")
    response = client.get("/notifications")
    assert response.status_code == 200
    assert b"You have no notifications yet." in response.data


def test_same_status_submission_does_not_create_duplicate_notification(client):
    complaint_id = create_owner_complaint_and_admin(client)
    client.post(f"/admin/complaints/{complaint_id}/status", data={"status": "In Progress"})
    client.post(f"/admin/complaints/{complaint_id}/status", data={"status": "In Progress"})
    with complaint_app.app.app_context():
        count = complaint_app.get_db().execute(
            "SELECT COUNT(*) FROM notifications WHERE complaint_id = ?", (complaint_id,)
        ).fetchone()[0]
    assert count == 1
