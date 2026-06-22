"""HTTP controller (APIRouter) for the Courses service.

Exposes course CRUD and grade endpoints. The endpoints
``GET /courses/{code}`` and ``GET /grades/{student_id}/{course_code}`` are the
ones consumed over HTTP by Service A.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.data.database import get_db
from app.schemas import (
    CourseCreate,
    CourseOut,
    CourseUpdate,
    GradeCreate,
    GradeOut,
)
from app.services.course_service import (
    CourseAlreadyExistsError,
    CourseNotFoundError,
    CourseService,
    GradeNotFoundError,
    GradeRangeError,
)

router = APIRouter(tags=["courses"])


def get_service() -> CourseService:
    """Dependency providing the service. Overridable in tests."""
    return CourseService()


# ----- Courses -----------------------------------------------------------
@router.post(
    "/courses", response_model=CourseOut, status_code=status.HTTP_201_CREATED
)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    service: CourseService = Depends(get_service),
) -> CourseOut:
    try:
        course = service.create_course(
            db, payload.code, payload.title, payload.credits
        )
    except CourseAlreadyExistsError as exc:
        raise HTTPException(
            status_code=409, detail=f"course already exists: {exc}"
        ) from exc
    return CourseOut.model_validate(course)


@router.get("/courses", response_model=list[CourseOut])
def list_courses(
    db: Session = Depends(get_db),
    service: CourseService = Depends(get_service),
) -> list[CourseOut]:
    return [CourseOut.model_validate(c) for c in service.list_courses(db)]


@router.get("/courses/{code}", response_model=CourseOut)
def get_course(
    code: str,
    db: Session = Depends(get_db),
    service: CourseService = Depends(get_service),
) -> CourseOut:
    """Fetch a single course. Consumed by Service A to validate enrollments."""
    try:
        course = service.get_course(db, code)
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="course not found") from exc
    return CourseOut.model_validate(course)


@router.put("/courses/{code}", response_model=CourseOut)
def update_course(
    code: str,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    service: CourseService = Depends(get_service),
) -> CourseOut:
    try:
        course = service.update_course(
            db, code, payload.title, payload.credits
        )
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="course not found") from exc
    return CourseOut.model_validate(course)


@router.delete("/courses/{code}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    code: str,
    db: Session = Depends(get_db),
    service: CourseService = Depends(get_service),
) -> None:
    try:
        service.delete_course(db, code)
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="course not found") from exc


# ----- Grades ------------------------------------------------------------
@router.post(
    "/grades", response_model=GradeOut, status_code=status.HTTP_201_CREATED
)
def record_grade(
    payload: GradeCreate,
    db: Session = Depends(get_db),
    service: CourseService = Depends(get_service),
) -> GradeOut:
    try:
        grade = service.record_grade(
            db, payload.student_id, payload.course_code, payload.value
        )
    except GradeRangeError as exc:
        raise HTTPException(
            status_code=422, detail=f"grade out of range (0..20): {exc}"
        ) from exc
    except CourseNotFoundError as exc:
        raise HTTPException(status_code=404, detail="course not found") from exc
    return GradeOut.model_validate(grade)


@router.get("/grades", response_model=list[GradeOut])
def list_grades(
    db: Session = Depends(get_db),
    service: CourseService = Depends(get_service),
) -> list[GradeOut]:
    return [GradeOut.model_validate(g) for g in service.list_grades(db)]


@router.get("/grades/{student_id}/{course_code}", response_model=GradeOut)
def get_grade(
    student_id: int,
    course_code: str,
    db: Session = Depends(get_db),
    service: CourseService = Depends(get_service),
) -> GradeOut:
    """Fetch a student's grade for a course. Consumed by Service A's transcript."""
    try:
        grade = service.get_grade(db, student_id, course_code)
    except GradeNotFoundError as exc:
        raise HTTPException(status_code=404, detail="grade not found") from exc
    return GradeOut.model_validate(grade)
