"""Assignment submission portal: Flask + SQLite."""
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlsplit

from flask import Flask, flash, redirect, render_template, request, url_for

FIELDS = ("student_name", "registration_number", "assignment_title", "submission_url")


def validate_submission(values):
    cleaned = {name: str(values.get(name, "")).strip() for name in FIELDS}
    errors = {}
    labels = {"student_name": "Student name", "registration_number": "Registration number",
              "assignment_title": "Assignment title", "submission_url": "Submission URL"}
    for field, label in labels.items():
        if not cleaned[field]:
            errors[field] = f"{label} is required."
    if cleaned["submission_url"]:
        try:
            parsed = urlsplit(cleaned["submission_url"])
            good = parsed.scheme in ("http", "https") and bool(parsed.hostname)
            # Reject invalid port and malformed whitespace.
            _ = parsed.port
            good = good and not any(c.isspace() for c in cleaned["submission_url"])
        except ValueError:
            good = False
        if not good:
            errors["submission_url"] = "Enter a valid http:// or https:// submission URL."
    return cleaned, errors


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(SECRET_KEY=os.environ.get("FLASK_SECRET_KEY", "development-only-secret"),
                      DATABASE=os.environ.get("PORTAL_DATABASE", str(Path(__file__).with_name("submissions.db"))),
                      TESTING=False)
    if config:
        app.config.update(config)

    def db_connection():
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        return connection

    with app.app_context():
        with db_connection() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    student_name TEXT NOT NULL,
                    registration_number TEXT NOT NULL,
                    assignment_title TEXT NOT NULL,
                    submission_url TEXT NOT NULL,
                    submitted_at TEXT NOT NULL DEFAULT (datetime('now'))
                )""")

    @app.get("/")
    def home():
        with db_connection() as con:
            submissions = con.execute("SELECT * FROM submissions ORDER BY id DESC").fetchall()
        return render_template("index.html", submissions=submissions, errors={}, old={})

    @app.post("/submit")
    def submit():
        values, errors = validate_submission(request.form)
        if errors:
            with db_connection() as con:
                submissions = con.execute("SELECT * FROM submissions ORDER BY id DESC").fetchall()
            return render_template("index.html", submissions=submissions, errors=errors, old=values), 400
        with db_connection() as con:
            con.execute("""INSERT INTO submissions
                (student_name, registration_number, assignment_title, submission_url)
                VALUES (?, ?, ?, ?)""", tuple(values[x] for x in FIELDS))
        flash("Assignment submitted successfully!", "success")
        return redirect(url_for("home"), code=303)

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
