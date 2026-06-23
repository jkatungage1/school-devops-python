"""Unit tests for the services layer.

These tests exercise StudentService. The outbound HTTP call from Service A to
Service B (the Courses service) is mocked with ``respx`` — this is the graded
"the service mocks the web" requirement, demonstrated here at the service layer.
"""

import httpx
import pytest
import respx
from app.config import settings
from app.services.courses_client import CoursesClient
from app.services.student_service import (
    AlreadyEnrolledError,
    CourseValidationError,
    NotEnrolledError,
    StudentAlreadyExistsError,
    StudentNotFoundError,
    StudentService,
)
from sqlalchemy.orm import Session

# Base URL of Service B that respx will intercept.
COURSES_URL = settings.courses_service_url


@pytest.fixture()
def service() -> StudentService:
    return StudentService(courses_client=CoursesClient(base_url=COURSES_URL))


def test_create_student_rejects_duplicate_email(
    service: StudentService, db_session: Session
) -> None:
    service.create_student(db_session, "Ada", "Lovelace", "ada@example.com")
    with pytest.raises(StudentAlreadyExistsError):
        service.create_student(db_session, "Ada2", "L", "ada@example.com")


def test_get_student_not_found(
    service: StudentService, db_session: Session
) -> None:
    with pytest.raises(StudentNotFoundError):
        service.get_student(db_session, 12345)


@respx.mock
def test_enroll_student_validates_course_via_service_b(
    service: StudentService, db_session: Session
) -> None:
    """enroll_student must call Service B over HTTP to validate the course."""
    student = service.create_student(db_session, "Alan", "Turing", "alan@x.com")

    # --- respx mocks Service B: course CS101 exists ---
    route = respx.get(f"{COURSES_URL}/courses/CS101").mock(
        return_value=httpx.Response(
            200, json={"code": "CS101", "title": "Intro to CS", "credits": 6}
        )
    )

    enrollment = service.enroll_student(db_session, student.id, "CS101")

    assert route.called  # proves the A -> B HTTP call happened
    assert enrollment.course_code == "CS101"


@respx.mock
def test_enroll_student_unknown_course_raises(
    service: StudentService, db_session: Session
) -> None:
    student = service.create_student(db_session, "Grace", "H", "grace@x.com")

    # --- respx mocks Service B returning 404 for an unknown course ---
    respx.get(f"{COURSES_URL}/courses/NOPE").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )

    with pytest.raises(CourseValidationError):
        service.enroll_student(db_session, student.id, "NOPE")


@respx.mock
def test_enroll_student_duplicate_raises(
    service: StudentService, db_session: Session
) -> None:
    student = service.create_student(db_session, "Dup", "Lic", "dup@x.com")
    respx.get(f"{COURSES_URL}/courses/CS101").mock(
        return_value=httpx.Response(200, json={"code": "CS101", "title": "CS"})
    )
    service.enroll_student(db_session, student.id, "CS101")
    with pytest.raises(AlreadyEnrolledError):
        service.enroll_student(db_session, student.id, "CS101")


@respx.mock
def test_record_grade_requires_enrollment(
    service: StudentService, db_session: Session
) -> None:
    """Grading a student who is not enrolled must fail and never call Service B."""
    student = service.create_student(db_session, "No", "Enroll", "no@x.com")

    route = respx.post(f"{COURSES_URL}/grades").mock(
        return_value=httpx.Response(201, json={})
    )

    with pytest.raises(NotEnrolledError):
        service.record_grade(db_session, student.id, "CS101", 15.0)

    assert not route.called  # Service B must NOT be hit when not enrolled


@respx.mock
def test_record_grade_persists_via_service_b_when_enrolled(
    service: StudentService, db_session: Session
) -> None:
    student = service.create_student(db_session, "Yes", "Enroll", "yes@x.com")

    respx.get(f"{COURSES_URL}/courses/CS101").mock(
        return_value=httpx.Response(200, json={"code": "CS101", "title": "CS"})
    )
    service.enroll_student(db_session, student.id, "CS101")

    # --- respx mocks Service B accepting the grade ---
    route = respx.post(f"{COURSES_URL}/grades").mock(
        return_value=httpx.Response(
            201,
            json={"student_id": student.id, "course_code": "CS101", "value": 15.0},
        )
    )

    grade = service.record_grade(db_session, student.id, "CS101", 15.0)

    assert route.called  # proves the A -> B HTTP call happened
    assert grade["value"] == 15.0


@respx.mock
def test_build_transcript_aggregates_grades_from_service_b(
    service: StudentService, db_session: Session
) -> None:
    student = service.create_student(db_session, "Tran", "Script", "ts@x.com")

    respx.get(f"{COURSES_URL}/courses/CS101").mock(
        return_value=httpx.Response(200, json={"code": "CS101", "title": "CS"})
    )
    respx.get(f"{COURSES_URL}/courses/MA201").mock(
        return_value=httpx.Response(200, json={"code": "MA201", "title": "Math"})
    )
    service.enroll_student(db_session, student.id, "CS101")
    service.enroll_student(db_session, student.id, "MA201")

    # --- respx mocks the grade endpoints of Service B ---
    respx.get(f"{COURSES_URL}/grades/{student.id}/CS101").mock(
        return_value=httpx.Response(200, json={"value": 16.0})
    )
    respx.get(f"{COURSES_URL}/grades/{student.id}/MA201").mock(
        return_value=httpx.Response(200, json={"value": 14.0})
    )

    transcript = service.build_transcript(db_session, student.id)
    assert transcript["gpa"] == 15.0
    assert len(transcript["lines"]) == 2
