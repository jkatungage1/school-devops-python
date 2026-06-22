"""Data-access layer: pure CRUD operations on the database.

Every function takes an explicit :class:`Session` so the layer stays free of
any web/HTTP concern and is trivial to unit-test against an in-memory SQLite.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.models import Enrollment, Student


class StudentRepository:
    """CRUD operations for :class:`Student` and :class:`Enrollment`."""

    # ----- Students -------------------------------------------------------
    @staticmethod
    def create(
        db: Session, first_name: str, last_name: str, email: str
    ) -> Student:
        student = Student(first_name=first_name, last_name=last_name, email=email)
        db.add(student)
        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def get(db: Session, student_id: int) -> Student | None:
        return db.get(Student, student_id)

    @staticmethod
    def get_by_email(db: Session, email: str) -> Student | None:
        return db.scalar(select(Student).where(Student.email == email))

    @staticmethod
    def list(db: Session) -> list[Student]:
        return list(db.scalars(select(Student).order_by(Student.id)))

    @staticmethod
    def update(
        db: Session,
        student_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> Student | None:
        student = db.get(Student, student_id)
        if student is None:
            return None
        if first_name is not None:
            student.first_name = first_name
        if last_name is not None:
            student.last_name = last_name
        if email is not None:
            student.email = email
        db.commit()
        db.refresh(student)
        return student

    @staticmethod
    def delete(db: Session, student_id: int) -> bool:
        student = db.get(Student, student_id)
        if student is None:
            return False
        db.delete(student)
        db.commit()
        return True

    # ----- Enrollments ----------------------------------------------------
    @staticmethod
    def add_enrollment(
        db: Session, student_id: int, course_code: str
    ) -> Enrollment:
        enrollment = Enrollment(student_id=student_id, course_code=course_code)
        db.add(enrollment)
        db.commit()
        db.refresh(enrollment)
        return enrollment

    @staticmethod
    def get_enrollment(
        db: Session, student_id: int, course_code: str
    ) -> Enrollment | None:
        return db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student_id,
                Enrollment.course_code == course_code,
            )
        )

    @staticmethod
    def list_enrollments(db: Session, student_id: int) -> list[Enrollment]:
        return list(
            db.scalars(
                select(Enrollment)
                .where(Enrollment.student_id == student_id)
                .order_by(Enrollment.id)
            )
        )
