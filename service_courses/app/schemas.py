"""Pydantic schemas for the Courses service."""

from pydantic import BaseModel, ConfigDict


class CourseCreate(BaseModel):
    """Payload to create a course."""

    code: str
    title: str
    credits: int = 3


class CourseUpdate(BaseModel):
    """Payload to update a course."""

    title: str | None = None
    credits: int | None = None


class CourseOut(BaseModel):
    """Course as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    code: str
    title: str
    credits: int


class GradeCreate(BaseModel):
    """Payload to record a grade for a student in a course."""

    student_id: int
    course_code: str
    value: float


class GradeOut(BaseModel):
    """Grade as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    student_id: int
    course_code: str
    value: float
