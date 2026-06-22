"""Unit tests for the data layer (CourseRepository) using in-memory SQLite."""

from app.data.repository import CourseRepository
from sqlalchemy.orm import Session


def test_create_and_get_course(db_session: Session) -> None:
    repo = CourseRepository()
    course = repo.create(db_session, "CS101", "Intro CS", 6)
    assert course.code == "CS101"
    fetched = repo.get(db_session, "CS101")
    assert fetched is not None
    assert fetched.title == "Intro CS"


def test_list_courses(db_session: Session) -> None:
    repo = CourseRepository()
    repo.create(db_session, "CS101", "Intro CS")
    repo.create(db_session, "MA201", "Algebra")
    assert len(repo.list(db_session)) == 2


def test_update_course(db_session: Session) -> None:
    repo = CourseRepository()
    repo.create(db_session, "CS101", "Intro CS", 6)
    updated = repo.update(db_session, "CS101", title="Advanced CS")
    assert updated is not None
    assert updated.title == "Advanced CS"
    assert repo.update(db_session, "NOPE", title="x") is None


def test_delete_course(db_session: Session) -> None:
    repo = CourseRepository()
    repo.create(db_session, "CS101", "Intro CS")
    assert repo.delete(db_session, "CS101") is True
    assert repo.delete(db_session, "CS101") is False


def test_grade_upsert_and_get(db_session: Session) -> None:
    repo = CourseRepository()
    repo.create(db_session, "CS101", "Intro CS")
    grade = repo.upsert_grade(db_session, 1, "CS101", 12.0)
    assert grade.value == 12.0
    # upsert again updates the value rather than duplicating.
    grade2 = repo.upsert_grade(db_session, 1, "CS101", 18.0)
    assert grade2.value == 18.0
    assert len(repo.list_grades(db_session)) == 1
    assert repo.get_grade(db_session, 1, "CS101") is not None
    assert repo.get_grade(db_session, 2, "CS101") is None
