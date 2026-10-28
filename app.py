
import os
import sqlite3
from functools import wraps
from flask import (
    Flask, abort, render_template, request, redirect,
    url_for, session, flash, g
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-key-change-before-deployment"
)
app.config["DATABASE"] = os.path.join(app.root_path, "complaints.db")

# Configure administrator access with a comma-separated ADMIN_EMAILS environment variable.
app.config["ADMIN_EMAILS"] = os.environ.get("ADMIN_EMAILS", "")
COMPLAINT_STATUSES = ("Submitted", "In Progress", "Resolved", "Rejected")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Other',
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Submitted',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)

    columns = {
        row["name"]
        for row in db.execute("PRAGMA table_info(complaints)").fetchall()
    }
    if "category" not in columns:
        db.execute(
            "ALTER TABLE complaints "
            "ADD COLUMN category TEXT NOT NULL DEFAULT 'Other'"
        )

    db.commit()


@app.before_request
def initialize_database():
    init_db()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped_view


def configured_admin_emails():
    configured = app.config.get("ADMIN_EMAILS", "")
    if isinstance(configured, str):
        values = configured.split(",")
    else:
        values = configured
    return {
        str(email).strip().lower()
        for email in values
        if str(email).strip()
    }


def current_user_is_admin():
    user_id = session.get("user_id")
    if user_id is None:
        return False
    user = get_db().execute(
        "SELECT email FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    return user is not None and user["email"].strip().lower() in configured_admin_emails()


@app.context_processor
def inject_admin_access():
    return {"current_user_is_admin": current_user_is_admin}


def admin_required(view):
    """Allow only logged-in users whose database email is explicitly configured as admin."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.")
            return redirect(url_for("login"))
        if not current_user_is_admin():
            abort(403)
        return view(*args, **kwargs)
    return wrapped_view

@app.route("/")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    complaints = get_db().execute(
        """SELECT * FROM complaints
           WHERE user_id = ? ORDER BY id DESC""",
        (session["user_id"],)
    ).fetchall()

    return render_template("dashboard.html", complaints=complaints)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("All fields are required.")
            return render_template("register.html")

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return render_template("register.html")

        try:
            db = get_db()
            db.execute(
                """INSERT INTO users (name, email, password_hash)
                   VALUES (?, ?, ?)""",
                (name, email, generate_password_hash(password))
            )
            db.commit()
        except sqlite3.IntegrityError:
            flash("An account with this email already exists.")
            return render_template("register.html")

        flash("Registration successful. Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = get_db().execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()

        if user is None or not check_password_hash(
            user["password_hash"], password
        ):
            flash("Invalid email or password.")
            return render_template("login.html")

        session.clear()
        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/complaints/new", methods=["GET", "POST"])
@login_required
def lodge_complaint():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()

        allowed_categories = {
            "Infrastructure",
            "Electrical",
            "Water Supply",
            "Cleanliness",
            "Other",
        }

        if not title or not category or not description:
            flash("Title, category, and description are required.")
            return render_template("lodge_complaint.html")

        if category not in allowed_categories:
            flash("Please select a valid complaint category.")
            return render_template("lodge_complaint.html")

        db = get_db()
        cursor = db.execute(
            """INSERT INTO complaints
               (user_id, title, category, description)
               VALUES (?, ?, ?, ?)""",
            (session["user_id"], title, category, description)
        )
        db.commit()

        # The database-generated ID uniquely identifies this complaint.
        complaint_id = cursor.lastrowid
        return redirect(url_for("track_complaint",
                                complaint_id=complaint_id))

    return render_template("lodge_complaint.html")


@app.route("/complaints/<int:complaint_id>")
@login_required
def track_complaint(complaint_id):
    complaint = get_db().execute(
        """SELECT * FROM complaints
           WHERE id = ? AND user_id = ?""",
        (complaint_id, session["user_id"])
    ).fetchone()

    if complaint is None:
        flash("Complaint not found.")
        return redirect(url_for("dashboard"))

    return render_template(
        "track_complaint.html", complaint=complaint
    )



@app.route("/admin/complaints")
@admin_required
def admin_complaints():
    search_query = request.args.get("q", "").strip()
    selected_status = request.args.get("status", "").strip()

    if selected_status and selected_status not in COMPLAINT_STATUSES:
        selected_status = ""

    sql = """
        SELECT complaints.*,
               users.name AS user_name,
               users.email AS user_email
        FROM complaints
        JOIN users ON users.id = complaints.user_id
        WHERE 1 = 1
    """
    params = []

    if search_query:
        term = f"%{search_query}%"
        sql += """
            AND (
                CAST(complaints.id AS TEXT) LIKE ?
                OR complaints.title LIKE ?
                OR complaints.description LIKE ?
                OR users.name LIKE ?
                OR users.email LIKE ?
            )
        """
        params.extend([term, term, term, term, term])

    if selected_status:
        sql += " AND complaints.status = ?"
        params.append(selected_status)

    sql += " ORDER BY complaints.id DESC"

    try:
        complaints = get_db().execute(sql, params).fetchall()
    except sqlite3.DatabaseError:
        app.logger.exception("Could not load complaints for admin")
        flash("Unable to load complaints right now.")
        complaints = []

    return render_template(
        "admin_complaints.html",
        complaints=complaints,
        complaint_statuses=COMPLAINT_STATUSES,
        search_query=search_query,
        selected_status=selected_status,
    )


@app.route("/admin/complaints/<int:complaint_id>/status", methods=["POST"])
@admin_required
def update_complaint_status(complaint_id):
    new_status = request.form.get("status", "").strip()
    if new_status not in COMPLAINT_STATUSES:
        flash("Invalid complaint status.")
        return redirect(url_for("admin_complaints"))

    db = get_db()
    try:
        cursor = db.execute(
            "UPDATE complaints SET status = ? WHERE id = ?",
            (new_status, complaint_id),
        )
        if cursor.rowcount == 0:
            db.rollback()
            abort(404)
        db.commit()
    except sqlite3.DatabaseError:
        db.rollback()
        app.logger.exception("Could not update complaint status")
        flash("Unable to update the complaint status. Please try again.")
        return redirect(url_for("admin_complaints"))

    flash(f"Complaint #{complaint_id} status updated to {new_status}.")
    return redirect(url_for("admin_complaints"))


if __name__ == "__main__":
    app.run(debug=True)
