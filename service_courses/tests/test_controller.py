"""Controller-level tests for the Courses service using FastAPI TestClient."""

from fastapi.testclient import TestClient


def test_course_crud(client: TestClient) -> None:
    resp = client.post(
        "/courses",
        json={"code": "CS101", "title": "Intro CS", "credits": 6},
    )
    assert resp.status_code == 201
    assert resp.json()["code"] == "CS101"

    # duplicate -> 409
    assert (
        client.post(
            "/courses", json={"code": "CS101", "title": "x", "credits": 1}
        ).status_code
        == 409
    )

    assert client.get("/courses/CS101").status_code == 200
    assert client.get("/courses/NOPE").status_code == 404

    listed = client.get("/courses")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    upd = client.put("/courses/CS101", json={"title": "Advanced CS"})
    assert upd.status_code == 200
    assert upd.json()["title"] == "Advanced CS"

    assert client.delete("/courses/CS101").status_code == 204
    assert client.get("/courses/CS101").status_code == 404


def test_grade_endpoints(client: TestClient) -> None:
    client.post(
        "/courses", json={"code": "CS101", "title": "Intro CS", "credits": 6}
    )

    resp = client.post(
        "/grades",
        json={"student_id": 1, "course_code": "CS101", "value": 15.0},
    )
    assert resp.status_code == 201

    got = client.get("/grades/1/CS101")
    assert got.status_code == 200
    assert got.json()["value"] == 15.0

    assert client.get("/grades/99/CS101").status_code == 404

    # out of range
    bad = client.post(
        "/grades",
        json={"student_id": 1, "course_code": "CS101", "value": 99.0},
    )
    assert bad.status_code == 422

    # grade for unknown course
    missing = client.post(
        "/grades",
        json={"student_id": 1, "course_code": "NOPE", "value": 10.0},
    )
    assert missing.status_code == 404

    assert client.get("/grades").status_code == 200


def test_health(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "courses"
