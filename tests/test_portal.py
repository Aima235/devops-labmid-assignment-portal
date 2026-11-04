"""The three mandatory assessed cases, plus coverage for missing other fields."""
import sqlite3
import pytest
from app import create_app

VALID = {"student_name": "Aima Perveen", "registration_number": "FA23-BAI-066",
         "assignment_title": "Lab Mid", "submission_url": "https://github.com/example/assignment"}

@pytest.fixture
def client(tmp_path):
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})
    with app.test_client() as test_client:
        yield test_client


def count(client):
    with sqlite3.connect(client.application.config["DATABASE"]) as con:
        return con.execute("SELECT COUNT(*) FROM submissions").fetchone()[0]


def test_valid_submission_is_saved_and_displayed(client):
    response = client.post("/submit", data=VALID, follow_redirects=True)
    assert response.status_code == 200
    assert b"Assignment submitted successfully" in response.data
    assert b"Aima Perveen" in response.data
    assert b"FA23-BAI-066" in response.data
    assert b"https://github.com/example/assignment" in response.data
    assert count(client) == 1


def test_missing_registration_number_is_rejected(client):
    response = client.post("/submit", data={**VALID, "registration_number": ""})
    assert response.status_code == 400
    assert b"Registration number is required" in response.data
    assert count(client) == 0


def test_invalid_url_is_rejected_and_not_saved(client):
    response = client.post("/submit", data={**VALID, "submission_url": "not-a-url"})
    assert response.status_code == 400
    assert b"Enter a valid http:// or https:// submission URL" in response.data
    assert count(client) == 0


@pytest.mark.parametrize("missing", ["student_name", "assignment_title", "submission_url"])
def test_other_required_fields_are_rejected(client, missing):
    response = client.post("/submit", data={**VALID, missing: ""})
    assert response.status_code == 400
    assert count(client) == 0
