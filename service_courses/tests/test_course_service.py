"""Unit tests for the services layer (CourseService)."""

import pytest
from app.services.course_service import (
    CourseAlreadyExistsError,
    CourseNotFoundError,
    CourseService,
    GradeNotFoundError,
    GradeRangeError,
)
from sqlalchemy.orm import Session


@pytest.fixture()
def service() -> CourseService:
    return CourseService()


def test_create_course_rejects_duplicate(
    service: CourseService, db_session: Session
) -> None:
    service.create_course(db_session, "CS101", "Intro CS", 6)
    with pytest.raises(CourseAlreadyExistsError):
        service.create_course(db_session, "CS101", "Dup", 6)


def test_get_course_not_found(
    service: CourseService, db_session: Session
) -> None:
    with pytest.raises(CourseNotFoundError):
        service.get_course(db_session, "NOPE")


def test_record_grade_validates_range(
    service: CourseService, db_session: Session
) -> None:
    service.create_course(db_session, "CS101", "Intro CS")
    with pytest.raises(GradeRangeError):
        service.record_grade(db_session, 1, "CS101", 21.0)
    with pytest.raises(GradeRangeError):
        service.record_grade(db_session, 1, "CS101", -1.0)


def test_record_grade_requires_course(
    service: CourseService, db_session: Session
) -> None:
    with pytest.raises(CourseNotFoundError):
        service.record_grade(db_session, 1, "NOPE", 15.0)


def test_record_and_get_grade(
    service: CourseService, db_session: Session
) -> None:
    service.create_course(db_session, "CS101", "Intro CS")
    grade = service.record_grade(db_session, 1, "CS101", 17.0)
    assert grade.value == 17.0
    assert service.get_grade(db_session, 1, "CS101").value == 17.0
    with pytest.raises(GradeNotFoundError):
        service.get_grade(db_session, 99, "CS101")


def test_seed_if_empty(service: CourseService, db_session: Session) -> None:
    service.seed_if_empty(db_session)
    assert len(service.list_courses(db_session)) >= 4
    # Running again is a no-op.
    service.seed_if_empty(db_session)
    assert len(service.list_courses(db_session)) >= 4


def test_update_and_delete_course(
    service: CourseService, db_session: Session
) -> None:
    service.create_course(db_session, "CS101", "Intro CS")
    updated = service.update_course(db_session, "CS101", title="Adv CS")
    assert updated.title == "Adv CS"
    service.delete_course(db_session, "CS101")
    with pytest.raises(CourseNotFoundError):
        service.delete_course(db_session, "CS101")
