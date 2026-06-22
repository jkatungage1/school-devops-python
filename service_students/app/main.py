"""FastAPI application entrypoint for the Students service (Service A)."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.students_controller import router as students_router
from app.data.database import Base, engine

# Create the database tables on startup (idempotent).
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Students Service",
    description="Service A - manages students and enrollments. "
    "Calls the Courses service (Service B) over HTTP to validate "
    "courses and fetch grades.",
    version="1.0.0",
)

# The frontend is served from a different origin (nginx on :8080), so allow CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(students_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Simple liveness probe used by docker-compose / CI."""
    return {"status": "ok", "service": "students"}
