"""HTTP controller (APIRouter) for the Students service.

Thin layer: it validates input via Pydantic schemas, delegates to
:class:`StudentService`, and maps domain exceptions to HTTP status codes.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.data.database import get_db
from app.schemas import (
    EnrollmentCreate,
    EnrollmentOut,
    StudentCreate,
    StudentOut,
    StudentUpdate,
    TranscriptOut,
)
from app.services.courses_client import CoursesServiceUnavailableError
from app.services.student_service import (
    AlreadyEnrolledError,
    CourseValidationError,
    StudentAlreadyExistsError,
    StudentNotFoundError,
    StudentService,
)

router = APIRouter(prefix="/students", tags=["students"])


def get_service() -> StudentService:
    """Dependency providing the service. Overridable in tests."""
    return StudentService()


@router.post("", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreate,
    db: Session = Depends(get_db),
    service: StudentService = Depends(get_service),
) -> StudentOut:
    try:
        student = service.create_student(
            db, payload.first_name, payload.last_name, payload.email
        )
    except StudentAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"email already registered: {exc}",
        ) from exc
    return StudentOut.model_validate(student)


@router.get("", response_model=list[StudentOut])
def list_students(
    db: Session = Depends(get_db),
    service: StudentService = Depends(get_service),
) -> list[StudentOut]:
    return [StudentOut.model_validate(s) for s in service.list_students(db)]


@router.get("/{student_id}", response_model=StudentOut)
def get_student(
    student_id: int,
    db: Session = Depends(get_db),
    service: StudentService = Depends(get_service),
) -> StudentOut:
    try:
        student = service.get_student(db, student_id)
    except StudentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="student not found") from exc
    return StudentOut.model_validate(student)


@router.put("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    payload: StudentUpdate,
    db: Session = Depends(get_db),
    service: StudentService = Depends(get_service),
) -> StudentOut:
    try:
        student = service.update_student(
            db,
            student_id,
            payload.first_name,
            payload.last_name,
            payload.email,
        )
    except StudentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="student not found") from exc
    return StudentOut.model_validate(student)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: int,
    db: Session = Depends(get_db),
    service: StudentService = Depends(get_service),
) -> None:
    try:
        service.delete_student(db, student_id)
    except StudentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="student not found") from exc


@router.post(
    "/{student_id}/enroll",
    response_model=EnrollmentOut,
    status_code=status.HTTP_201_CREATED,
)
def enroll_student(
    student_id: int,
    payload: EnrollmentCreate,
    db: Session = Depends(get_db),
    service: StudentService = Depends(get_service),
) -> EnrollmentOut:
    """Enroll a student into a course.

    Triggers an HTTP call to Service B to validate the course code.
    """
    try:
        enrollment = service.enroll_student(db, student_id, payload.course_code)
    except StudentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="student not found") from exc
    except CourseValidationError as exc:
        raise HTTPException(
            status_code=422, detail=f"unknown course code: {exc}"
        ) from exc
    except AlreadyEnrolledError as exc:
        raise HTTPException(
            status_code=409, detail=f"already enrolled in {exc}"
        ) from exc
    except CoursesServiceUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="courses service unavailable"
        ) from exc
    return EnrollmentOut.model_validate(enrollment)


@router.get("/{student_id}/transcript", response_model=TranscriptOut)
def get_transcript(
    student_id: int,
    db: Session = Depends(get_db),
    service: StudentService = Depends(get_service),
) -> TranscriptOut:
    """Return a transcript, fetching grades from Service B per course."""
    try:
        transcript = service.build_transcript(db, student_id)
    except StudentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="student not found") from exc
    except CoursesServiceUnavailableError as exc:
        raise HTTPException(
            status_code=503, detail="courses service unavailable"
        ) from exc
    return TranscriptOut.model_validate(transcript)
