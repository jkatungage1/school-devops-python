"""Business logic for students and enrollments.

This layer orchestrates the data layer (:class:`StudentRepository`) and the
cross-service HTTP client (:class:`CoursesClient`). Notably, ``enroll_student``
validates the course against Service B *before* persisting an enrollment, and
``build_transcript`` aggregates grades fetched from Service B.
"""

from sqlalchemy.orm import Session

from app.data.models import Enrollment, Student
from app.data.repository import StudentRepository
from app.services.courses_client import (
    CourseNotFoundError,
    CoursesClient,
)


class StudentAlreadyExistsError(Exception):
    """Raised when creating a student with an email that already exists."""


class StudentNotFoundError(Exception):
    """Raised when an operation targets a non-existent student."""


class CourseValidationError(Exception):
    """Raised when enrolling into a course that Service B does not know."""


class AlreadyEnrolledError(Exception):
    """Raised when a student is already enrolled in the given course."""


class NotEnrolledError(Exception):
    """Raised when grading a student for a course they are not enrolled in."""


class StudentService:
    """Use-cases for the Students service."""

    def __init__(
        self,
        repo: StudentRepository | None = None,
        courses_client: CoursesClient | None = None,
    ):
        self.repo = repo or StudentRepository()
        self.courses_client = courses_client or CoursesClient()

    # ----- Student CRUD ---------------------------------------------------
    def create_student(
        self, db: Session, first_name: str, last_name: str, email: str
    ) -> Student:
        if self.repo.get_by_email(db, email) is not None:
            raise StudentAlreadyExistsError(email)
        return self.repo.create(db, first_name, last_name, email)

    def get_student(self, db: Session, student_id: int) -> Student:
        student = self.repo.get(db, student_id)
        if student is None:
            raise StudentNotFoundError(student_id)
        return student

    def list_students(self, db: Session) -> list[Student]:
        return self.repo.list(db)

    def update_student(
        self,
        db: Session,
        student_id: int,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> Student:
        student = self.repo.update(db, student_id, first_name, last_name, email)
        if student is None:
            raise StudentNotFoundError(student_id)
        return student

    def delete_student(self, db: Session, student_id: int) -> None:
        if not self.repo.delete(db, student_id):
            raise StudentNotFoundError(student_id)

    # ----- Enrollment (A -> B HTTP call lives here) -----------------------
    def enroll_student(
        self, db: Session, student_id: int, course_code: str
    ) -> Enrollment:
        """Enroll a student into a course.

        Steps:
          1. Ensure the student exists (local DB).
          2. Validate the course code by calling Service B over HTTP.
             *This outbound call is what respx mocks in the tests.*
          3. Persist the enrollment (rejecting duplicates).
        """
        student = self.repo.get(db, student_id)
        if student is None:
            raise StudentNotFoundError(student_id)

        # --- cross-service validation: ask Service B if the course exists ---
        try:
            self.courses_client.get_course(course_code)
        except CourseNotFoundError as exc:
            raise CourseValidationError(course_code) from exc

        if self.repo.get_enrollment(db, student_id, course_code) is not None:
            raise AlreadyEnrolledError(course_code)

        return self.repo.add_enrollment(db, student_id, course_code)

    def record_grade(
        self, db: Session, student_id: int, course_code: str, value: float
    ) -> dict:
        """Record a grade for a student, but only if they are enrolled.

        Enrollment is owned by Service A, so the rule is enforced here before
        the grade is persisted in Service B via an A -> B HTTP call.
        """
        student = self.repo.get(db, student_id)
        if student is None:
            raise StudentNotFoundError(student_id)

        if self.repo.get_enrollment(db, student_id, course_code) is None:
            raise NotEnrolledError(course_code)

        # --- A -> B HTTP call to persist the grade ---
        return self.courses_client.record_grade(student_id, course_code, value)

    def build_transcript(self, db: Session, student_id: int) -> dict:
        """Build a transcript by fetching each course's grade from Service B."""
        student = self.repo.get(db, student_id)
        if student is None:
            raise StudentNotFoundError(student_id)

        enrollments = self.repo.list_enrollments(db, student_id)
        lines: list[dict] = []
        grades: list[float] = []
        for enrollment in enrollments:
            course_title: str | None = None
            try:
                course = self.courses_client.get_course(enrollment.course_code)
                course_title = course.get("title")
            except CourseNotFoundError:
                course_title = None

            # --- A -> B HTTP call to fetch the grade ---
            grade = self.courses_client.get_grade(
                student_id, enrollment.course_code
            )
            if grade is not None:
                grades.append(grade)
            lines.append(
                {
                    "course_code": enrollment.course_code,
                    "course_title": course_title,
                    "grade": grade,
                }
            )

        gpa = round(sum(grades) / len(grades), 2) if grades else None
        return {
            "student_id": student.id,
            "student_name": f"{student.first_name} {student.last_name}",
            "lines": lines,
            "gpa": gpa,
        }
