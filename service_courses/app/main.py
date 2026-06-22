"""FastAPI application entrypoint for the Courses service (Service B)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.courses_controller import router as courses_router
from app.data.database import Base, SessionLocal, engine
from app.services.course_service import CourseService

# Create the database tables on startup (idempotent).
Base.metadata.create_all(bind=engine)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Seed a couple of demo courses so the dashboard isn't empty on boot."""
    db = SessionLocal()
    try:
        CourseService().seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="Courses Service",
    description="Service B - manages courses and grades. Consumed by the "
    "Students service (Service A) over HTTP.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(courses_router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """Simple liveness probe used by docker-compose / CI."""
    return {"status": "ok", "service": "courses"}
