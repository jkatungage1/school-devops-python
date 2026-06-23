"""HTTP client wrapping calls to Service B (the Courses service).

This module is the ONLY place where Service A talks to Service B. The calls go
out over HTTP via ``httpx`` against the base URL configured in
``settings.courses_service_url``. In the test-suite these outbound calls are
intercepted and stubbed with ``respx`` (see tests/) — that is the graded
"the service mocks the web" requirement.
"""

import httpx

from app.config import settings


class CourseNotFoundError(Exception):
    """Raised when Service B reports a course code does not exist."""


class CoursesServiceUnavailableError(Exception):
    """Raised when Service B cannot be reached or returns a server error."""


class GradeRejectedError(Exception):
    """Raised when Service B rejects a grade (e.g. value out of range)."""


class CoursesClient:
    """Thin synchronous wrapper around Service B's HTTP API."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        self.base_url = (base_url or settings.courses_service_url).rstrip("/")
        self.timeout = timeout or settings.http_timeout

    def get_course(self, course_code: str) -> dict:
        """Fetch a course from Service B. Raises if it does not exist.

        Makes ``GET {COURSES_SERVICE_URL}/courses/{course_code}``.
        """
        url = f"{self.base_url}/courses/{course_code}"
        try:
            response = httpx.get(url, timeout=self.timeout)
        except httpx.HTTPError as exc:  # network/connection error
            raise CoursesServiceUnavailableError(str(exc)) from exc

        if response.status_code == 404:
            raise CourseNotFoundError(course_code)
        if response.status_code >= 500:
            raise CoursesServiceUnavailableError(
                f"courses service returned {response.status_code}"
            )
        response.raise_for_status()
        return response.json()

    def get_grade(self, student_id: int, course_code: str) -> float | None:
        """Fetch a student's grade for a course from Service B.

        Makes ``GET {COURSES_SERVICE_URL}/grades/{student_id}/{course_code}``.
        Returns ``None`` when no grade has been recorded yet (HTTP 404).
        """
        url = f"{self.base_url}/grades/{student_id}/{course_code}"
        try:
            response = httpx.get(url, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise CoursesServiceUnavailableError(str(exc)) from exc

        if response.status_code == 404:
            return None
        if response.status_code >= 500:
            raise CoursesServiceUnavailableError(
                f"courses service returned {response.status_code}"
            )
        response.raise_for_status()
        return float(response.json()["value"])

    def record_grade(
        self, student_id: int, course_code: str, value: float
    ) -> dict:
        """Persist a grade in Service B. Raises if B rejects it.

        Makes ``POST {COURSES_SERVICE_URL}/grades``. Enrollment is *not* checked
        here — that is Service A's responsibility before this call is made.
        """
        url = f"{self.base_url}/grades"
        payload = {
            "student_id": student_id,
            "course_code": course_code,
            "value": value,
        }
        try:
            response = httpx.post(url, json=payload, timeout=self.timeout)
        except httpx.HTTPError as exc:
            raise CoursesServiceUnavailableError(str(exc)) from exc

        if response.status_code == 404:
            raise CourseNotFoundError(course_code)
        if response.status_code >= 500:
            raise CoursesServiceUnavailableError(
                f"courses service returned {response.status_code}"
            )
        if response.status_code >= 400:
            detail = response.json().get("detail", "grade rejected")
            raise GradeRejectedError(detail)
        return response.json()
