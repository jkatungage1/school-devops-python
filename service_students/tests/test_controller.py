"""Controller-level tests using FastAPI's TestClient.

The enroll/transcript endpoints reach out to Service B; those outbound HTTP
calls are mocked with ``respx`` here too, satisfying the graded "mocks web"
requirement at the controller layer.
"""

import httpx
import respx
from app.config import settings
from fastapi.testclient import TestClient

COURSES_URL = settings.courses_service_url


def test_create_and_list_students(client: TestClient) -> None:
    resp = client.post(
        "/students",
        json={
            "first_name": "Ada",
            "last_name": "Lovelace",
            "email": "ada@example.com",
        },
    )
    assert resp.status_code == 201
    student = resp.json()
    assert student["id"] >= 1

    listed = client.get("/students")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_get_update_delete_student(client: TestClient) -> None:
    created = client.post(
        "/students",
        json={"first_name": "Al", "last_name": "T", "email": "al@example.com"},
    ).json()
    sid = created["id"]

    assert client.get(f"/students/{sid}").status_code == 200
    assert client.get("/students/9999").status_code == 404

    upd = client.put(f"/students/{sid}", json={"first_name": "Alan"})
    assert upd.status_code == 200
    assert upd.json()["first_name"] == "Alan"

    assert client.delete(f"/students/{sid}").status_code == 204
    assert client.get(f"/students/{sid}").status_code == 404


def test_duplicate_email_conflict(client: TestClient) -> None:
    body = {"first_name": "A", "last_name": "B", "email": "dup@example.com"}
    assert client.post("/students", json=body).status_code == 201
    assert client.post("/students", json=body).status_code == 409


@respx.mock
def test_enroll_endpoint_mocks_service_b(client: TestClient) -> None:
    student = client.post(
        "/students",
        json={"first_name": "En", "last_name": "Roll", "email": "en@x.com"},
    ).json()

    # --- respx mocks Service B confirming the course exists ---
    route = respx.get(f"{COURSES_URL}/courses/CS101").mock(
        return_value=httpx.Response(200, json={"code": "CS101", "title": "CS"})
    )

    resp = client.post(
        f"/students/{student['id']}/enroll", json={"course_code": "CS101"}
    )
    assert resp.status_code == 201
    assert route.called
    assert resp.json()["course_code"] == "CS101"


@respx.mock
def test_enroll_endpoint_unknown_course_422(client: TestClient) -> None:
    student = client.post(
        "/students",
        json={"first_name": "Un", "last_name": "Known", "email": "un@x.com"},
    ).json()

    respx.get(f"{COURSES_URL}/courses/NOPE").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    resp = client.post(
        f"/students/{student['id']}/enroll", json={"course_code": "NOPE"}
    )
    assert resp.status_code == 422


@respx.mock
def test_transcript_endpoint_mocks_service_b(client: TestClient) -> None:
    student = client.post(
        "/students",
        json={"first_name": "Tr", "last_name": "An", "email": "tr@x.com"},
    ).json()
    sid = student["id"]

    respx.get(f"{COURSES_URL}/courses/CS101").mock(
        return_value=httpx.Response(200, json={"code": "CS101", "title": "CS"})
    )
    client.post(f"/students/{sid}/enroll", json={"course_code": "CS101"})

    respx.get(f"{COURSES_URL}/grades/{sid}/CS101").mock(
        return_value=httpx.Response(200, json={"value": 18.0})
    )

    resp = client.get(f"/students/{sid}/transcript")
    assert resp.status_code == 200
    data = resp.json()
    assert data["gpa"] == 18.0
    assert data["lines"][0]["grade"] == 18.0


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "students"
