"""Unit tests for the data layer (StudentRepository) using in-memory SQLite."""

from app.data.repository import StudentRepository
from sqlalchemy.orm import Session


def test_create_and_get_student(db_session: Session) -> None:
    repo = StudentRepository()
    student = repo.create(db_session, "Ada", "Lovelace", "ada@example.com")
    assert student.id is not None

    fetched = repo.get(db_session, student.id)
    assert fetched is not None
    assert fetched.email == "ada@example.com"


def test_get_by_email(db_session: Session) -> None:
    repo = StudentRepository()
    repo.create(db_session, "Alan", "Turing", "alan@example.com")
    found = repo.get_by_email(db_session, "alan@example.com")
    assert found is not None
    assert found.first_name == "Alan"
    assert repo.get_by_email(db_session, "missing@example.com") is None


def test_list_students(db_session: Session) -> None:
    repo = StudentRepository()
    repo.create(db_session, "A", "One", "a@example.com")
    repo.create(db_session, "B", "Two", "b@example.com")
    assert len(repo.list(db_session)) == 2


def test_update_student(db_session: Session) -> None:
    repo = StudentRepository()
    student = repo.create(db_session, "Grace", "Hopper", "grace@example.com")
    updated = repo.update(db_session, student.id, first_name="Gracie")
    assert updated is not None
    assert updated.first_name == "Gracie"
    assert repo.update(db_session, 9999, first_name="Nope") is None


def test_delete_student(db_session: Session) -> None:
    repo = StudentRepository()
    student = repo.create(db_session, "Del", "Ete", "del@example.com")
    assert repo.delete(db_session, student.id) is True
    assert repo.get(db_session, student.id) is None
    assert repo.delete(db_session, student.id) is False


def test_enrollments(db_session: Session) -> None:
    repo = StudentRepository()
    student = repo.create(db_session, "En", "Roll", "en@example.com")
    enrollment = repo.add_enrollment(db_session, student.id, "CS101")
    assert enrollment.id is not None

    assert repo.get_enrollment(db_session, student.id, "CS101") is not None
    assert repo.get_enrollment(db_session, student.id, "NOPE") is None
    assert len(repo.list_enrollments(db_session, student.id)) == 1
