"""Data-access layer for the Courses service: pure CRUD on the database."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.data.models import Course, Grade


class CourseRepository:
    """CRUD operations for :class:`Course` and :class:`Grade`."""

    # ----- Courses --------------------------------------------------------
    @staticmethod
    def create(db: Session, code: str, title: str, credits: int = 3) -> Course:
        course = Course(code=code, title=title, credits=credits)
        db.add(course)
        db.commit()
        db.refresh(course)
        return course

    @staticmethod
    def get(db: Session, code: str) -> Course | None:
        return db.get(Course, code)

    @staticmethod
    def list(db: Session) -> list[Course]:
        return list(db.scalars(select(Course).order_by(Course.code)))

    @staticmethod
    def update(
        db: Session,
        code: str,
        title: str | None = None,
        credits: int | None = None,
    ) -> Course | None:
        course = db.get(Course, code)
        if course is None:
            return None
        if title is not None:
            course.title = title
        if credits is not None:
            course.credits = credits
        db.commit()
        db.refresh(course)
        return course

    @staticmethod
    def delete(db: Session, code: str) -> bool:
        course = db.get(Course, code)
        if course is None:
            return False
        db.delete(course)
        db.commit()
        return True

    # ----- Grades ---------------------------------------------------------
    @staticmethod
    def upsert_grade(
        db: Session, student_id: int, course_code: str, value: float
    ) -> Grade:
        grade = db.scalar(
            select(Grade).where(
                Grade.student_id == student_id,
                Grade.course_code == course_code,
            )
        )
        if grade is None:
            grade = Grade(
                student_id=student_id, course_code=course_code, value=value
            )
            db.add(grade)
        else:
            grade.value = value
        db.commit()
        db.refresh(grade)
        return grade

    @staticmethod
    def get_grade(
        db: Session, student_id: int, course_code: str
    ) -> Grade | None:
        return db.scalar(
            select(Grade).where(
                Grade.student_id == student_id,
                Grade.course_code == course_code,
            )
        )

    @staticmethod
    def list_grades(db: Session) -> list[Grade]:
        return list(db.scalars(select(Grade).order_by(Grade.id)))
