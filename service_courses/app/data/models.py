"""ORM models for the Courses service (SQLAlchemy 2.x typed style)."""

from sqlalchemy import Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.data.database import Base


class Course(Base):
    """A course offered by the school, identified by a unique code."""

    __tablename__ = "courses"

    code: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    credits: Mapped[int] = mapped_column(Integer, default=3)


class Grade(Base):
    """A grade obtained by a student (by id) in a course (by code)."""

    __tablename__ = "grades"
    __table_args__ = (
        UniqueConstraint("student_id", "course_code", name="uq_grade"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(Integer, index=True)
    course_code: Mapped[str] = mapped_column(String(50), index=True)
    value: Mapped[float] = mapped_column(Float)
