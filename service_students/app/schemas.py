"""Pydantic schemas (request/response models) for the Students service."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class StudentCreate(BaseModel):
    """Payload to create a new student."""

    first_name: str
    last_name: str
    email: EmailStr


class StudentUpdate(BaseModel):
    """Payload to update an existing student (all fields optional)."""

    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None


class StudentOut(BaseModel):
    """Student as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: EmailStr


class EnrollmentCreate(BaseModel):
    """Payload to enroll a student into a course."""

    course_code: str


class EnrollmentOut(BaseModel):
    """Enrollment as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    course_code: str
    enrolled_at: datetime


class TranscriptLine(BaseModel):
    """One line of a transcript: a course and the grade obtained for it."""

    course_code: str
    course_title: str | None = None
    grade: float | None = None


class TranscriptOut(BaseModel):
    """Full transcript for a student, aggregated from Service B."""

    student_id: int
    student_name: str
    lines: list[TranscriptLine]
    gpa: float | None = None
