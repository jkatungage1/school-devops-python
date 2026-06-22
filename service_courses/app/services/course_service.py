"""Business logic for courses and grades."""

from sqlalchemy.orm import Session

from app.data.models import Course, Grade
from app.data.repository import CourseRepository


class CourseAlreadyExistsError(Exception):
    """Raised when creating a course whose code already exists."""


class CourseNotFoundError(Exception):
    """Raised when an operation targets a non-existent course."""


class GradeNotFoundError(Exception):
    """Raised when a requested grade does not exist."""


class GradeRangeError(Exception):
    """Raised when a grade value is outside the accepted 0..20 range."""


class CourseService:
    """Use-cases for the Courses service."""

    def __init__(self, repo: CourseRepository | None = None):
        self.repo = repo or CourseRepository()

    # ----- Courses --------------------------------------------------------
    def create_course(
        self, db: Session, code: str, title: str, credits: int = 3
    ) -> Course:
        if self.repo.get(db, code) is not None:
            raise CourseAlreadyExistsError(code)
        return self.repo.create(db, code, title, credits)

    def get_course(self, db: Session, code: str) -> Course:
        course = self.repo.get(db, code)
        if course is None:
            raise CourseNotFoundError(code)
        return course

    def list_courses(self, db: Session) -> list[Course]:
        return self.repo.list(db)

    def update_course(
        self,
        db: Session,
        code: str,
        title: str | None = None,
        credits: int | None = None,
    ) -> Course:
        course = self.repo.update(db, code, title, credits)
        if course is None:
            raise CourseNotFoundError(code)
        return course

    def delete_course(self, db: Session, code: str) -> None:
        if not self.repo.delete(db, code):
            raise CourseNotFoundError(code)

    # ----- Grades ---------------------------------------------------------
    def record_grade(
        self, db: Session, student_id: int, course_code: str, value: float
    ) -> Grade:
        if value < 0 or value > 20:
            raise GradeRangeError(value)
        if self.repo.get(db, course_code) is None:
            raise CourseNotFoundError(course_code)
        return self.repo.upsert_grade(db, student_id, course_code, value)

    def get_grade(self, db: Session, student_id: int, course_code: str) -> Grade:
        grade = self.repo.get_grade(db, student_id, course_code)
        if grade is None:
            raise GradeNotFoundError((student_id, course_code))
        return grade

    def list_grades(self, db: Session) -> list[Grade]:
        return self.repo.list_grades(db)

    # ----- Seed -----------------------------------------------------------
    def seed_if_empty(self, db: Session) -> None:
        """Populate a few demo courses + grades when the DB is empty."""
        if self.repo.list(db):
            return
        self.repo.create(db, "CS101", "Introduction to Computer Science", 6)
        self.repo.create(db, "MA201", "Linear Algebra", 4)
        self.repo.create(db, "DEV301", "DevOps & Microservices", 5)
        self.repo.create(db, "WEB210", "Web Development", 3)
        # A couple of demo grades for student id 1.
        self.repo.upsert_grade(db, 1, "CS101", 16.0)
        self.repo.upsert_grade(db, 1, "MA201", 13.5)
