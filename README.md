# School DevOps Project — Two FastAPI Microservices

[![CI](https://github.com/jkatungage1/school-devops-python/actions/workflows/ci.yml/badge.svg)](https://github.com/jkatungage1/school-devops-python/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/jkatungage1/school-devops-python/branch/main/graph/badge.svg)](https://codecov.io/gh/jkatungage1/school-devops-python)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=jkatungage1_school-devops-python&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=jkatungage1_school-devops-python)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=jkatungage1_school-devops-python&metric=coverage)](https://sonarcloud.io/summary/new_code?id=jkatungage1_school-devops-python)

It is made of **two independent FastAPI services** that communicate **over HTTP**,
a **vanilla-JS dashboard**, a **docker-compose** stack, a **GitHub Actions CI**
pipeline, and a unit-test suite (each architectural layer tested separately,
with the cross-service HTTP call mocked using `respx`).

---

## 1. Architecture

```
                          ┌──────────────────────────────┐
                          │         FRONTEND (SPA)        │
                          │   nginx static · :8080        │
                          │   index.html / app.js / css   │
                          └───────────┬──────────┬────────┘
                          fetch :8001 │          │ fetch :8002
                                      ▼          ▼
        ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
        │   SERVICE A — STUDENTS  :8001    │   │   SERVICE B — COURSES   :8002    │
        │   (FastAPI)                      │   │   (FastAPI)                      │
        │ ┌─────────────────────────────┐ │   │ ┌─────────────────────────────┐ │
        │ │ Controller (APIRouter)      │ │   │ │ Controller (APIRouter)      │ │
        │ ├─────────────────────────────┤ │   │ ├─────────────────────────────┤ │
        │ │ Services (business logic)   │ │   │ │ Services (business logic)   │ │
        │ │   StudentService            │ │   │ │   CourseService             │ │
        │ │   CoursesClient (httpx) ────┼─┼───┼─┼──► GET /courses/{code}      │ │
        │ │                         ────┼─┼───┼─┼──► GET /grades/{sid}/{code} │ │
        │ ├─────────────────────────────┤ │   │ ├─────────────────────────────┤ │
        │ │ Data (SQLAlchemy 2.x)       │ │   │ │ Data (SQLAlchemy 2.x)       │ │
        │ │   StudentRepository         │ │   │ │   CourseRepository          │ │
        │ │   students.db (SQLite)      │ │   │ │   courses.db (SQLite)       │ │
        │ └─────────────────────────────┘ │   │ └─────────────────────────────┘ │
        └─────────────────────────────────┘   └─────────────────────────────────┘
                       A  ───────────  HTTP (httpx)  ───────────►  B
```

Each service follows a strict **3-layer split**:

| Layer          | Responsibility                                   | Students files                         | Courses files                        |
| -------------- | ------------------------------------------------ | -------------------------------------- | ------------------------------------ |
| **Controller** | HTTP routing, validation, status-code mapping    | `app/controllers/students_controller.py` | `app/controllers/courses_controller.py` |
| **Services**   | Business logic, cross-service calls              | `app/services/student_service.py`, `courses_client.py` | `app/services/course_service.py`     |
| **Data**       | ORM models + repository (pure CRUD on a Session) | `app/data/{models,repository,database}.py` | `app/data/{models,repository,database}.py` |

---

## 2. The A → B interaction (the "service consumes the web" requirement)

Service A never reads the courses database directly. Whenever it needs course
information it makes an **HTTP request to Service B** through
`app/services/courses_client.py` (using `httpx`):

1. **Enroll** — `POST /students/{id}/enroll`
   `StudentService.enroll_student()` calls `GET {COURSES_SERVICE_URL}/courses/{code}`
   to **validate the course exists** before persisting an `Enrollment`.
   - course missing → Service B returns `404` → Service A returns `422`.

2. **Transcript** — `GET /students/{id}/transcript`
   For each enrollment it calls
   `GET {COURSES_SERVICE_URL}/grades/{student_id}/{course_code}` to fetch the
   grade, then aggregates the GPA.

`COURSES_SERVICE_URL` comes from config (`app/config.py`); docker-compose sets
it to `http://courses:8002`. Locally it defaults to `http://localhost:8002`.

### Mocking the web in tests (`respx`)

The outbound A → B HTTP calls are stubbed with **`respx`** so the Students
service can be tested in isolation, without Service B running. *"the service mocks the web"* requirement is demonstrated at two
layers:

- **Service layer**: `service_students/tests/test_student_service.py`
  (`@respx.mock` on `test_enroll_student_validates_course_via_service_b`,
  `..._unknown_course_raises`, `test_build_transcript_aggregates_grades_from_service_b`).
- **Controller layer**: `service_students/tests/test_controller.py`
  (`@respx.mock` on `test_enroll_endpoint_mocks_service_b`,
  `test_transcript_endpoint_mocks_service_b`).

Each asserts `route.called` to prove the HTTP call actually fired.

---

## 3. How to run

### Option A — Docker (recommended)

```bash
docker compose up --build
```

Then open:

| URL                                   | What                                   |
| ------------------------------------- | -------------------------------------- |
| http://localhost:8080                 | **Dashboard** (the showpiece UI)       |
| http://localhost:8001/docs            | Students service — Swagger UI          |
| http://localhost:8002/docs            | Courses service — Swagger UI           |

Service B seeds a few demo courses on first boot, so the dashboard is populated
immediately.

### Option B — Locally (two terminals)

```bash
# terminal 1 — Courses (Service B) first
cd service_courses
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002

# terminal 2 — Students (Service A)
cd service_students
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Open `frontend/index.html` directly in a browser (it auto-targets `localhost`).

### Makefile shortcuts

```bash
make install      # install both services + dev tooling
make docker-up    # build & start the whole stack
make run-courses  # run Service B locally
make run-students # run Service A locally
```

---

## 4. How to test

```bash
make install      # one-time: installs deps + pytest, respx, ruff, ...

# all tests, both services
make test

# with coverage (target > 80%)
make cov
```

Or per service:

```bash
cd service_students && pytest --cov=app --cov-report=term-missing
cd service_courses  && pytest --cov=app --cov-report=term-missing
```

Lint:

```bash
make lint          # ruff check on both services
```

The same steps run automatically in **GitHub Actions**
(`.github/workflows/ci.yml`): checkout → setup-python 3.12 → install →
ruff → mypy (non-blocking) → pytest `--cov` for each service → upload coverage.

---

## 5. Requirement → Implementation mapping

| # | Requirement                                   | Where it is implemented                                                                 |
| - | --------------------------------------------- | -------------------------------------------------------------------------------------- |
| 1 | Two distinct microservices                    | `service_students/` (Service A, :8001), `service_courses/` (Service B, :8002)           |
| 2 | 3-layer architecture (Data / Services / Ctrl) | `app/data/`, `app/services/`, `app/controllers/` in **each** service                    |
| 3 | A service that consumes the web (HTTP A→B)    | `service_students/app/services/courses_client.py` (httpx → Service B)                   |
| 4 | Course validation before enrollment           | `StudentService.enroll_student()` → `CoursesClient.get_course()`                        |
| 5 | Transcript aggregates remote grades           | `StudentService.build_transcript()` → `CoursesClient.get_grade()`                       |
| 6 | Mock the web in tests (`respx`)               | `test_student_service.py`, `test_controller.py` (`@respx.mock`)                         |
| 7 | Each layer unit-tested                         | `test_repository.py` (data), `test_*_service.py` (services), `test_controller.py` (ctrl)|
| 8 | Persistence                                   | SQLAlchemy 2.x + SQLite (`students.db`, `courses.db`)                                   |
| 9 | Dependency injection                          | FastAPI `Depends(get_db)` + injectable service/client                                   |
| 10 | Containerization                             | `service_*/Dockerfile` (python:3.12-slim), `frontend/Dockerfile` (nginx)               |
| 11 | Orchestration                                | `docker-compose.yml` (students, courses, frontend; sets `COURSES_SERVICE_URL`)          |
| 12 | CI/CD pipeline                               | `.github/workflows/ci.yml` (lint + typecheck + tests + coverage)                        |
| 13 | Tooling config                               | `pyproject.toml` (ruff, black, mypy, pytest, coverage; line-length 100)                 |
| 14 | Polished frontend                            | `frontend/index.html`, `styles.css`, `app.js` (dark glassy dashboard)                  |

---

## 6. API summary

### Service A — Students (:8001)
- `POST   /students` — create
- `GET    /students` — list
- `GET    /students/{id}` — read
- `PUT    /students/{id}` — update
- `DELETE /students/{id}` — delete
- `POST   /students/{id}/enroll` — enroll (validates course via Service B)
- `GET    /students/{id}/transcript` — transcript (grades from Service B)
- `GET    /health`

### Service B — Courses (:8002)
- `POST   /courses` · `GET /courses` · `GET /courses/{code}` · `PUT /courses/{code}` · `DELETE /courses/{code}`
- `POST   /grades` · `GET /grades` · `GET /grades/{student_id}/{course_code}`
- `GET    /health`

---

## 7. Report screenshots

Screenshots for the written report live in `docs/screenshots/`:

- `dashboard.png` — the running dashboard at http://localhost:8080
- `swagger-students.png` — http://localhost:8001/docs
- `swagger-courses.png` — http://localhost:8002/docs
- `tests.png` — `make cov` output showing coverage > 80%
- `ci.png` — a green GitHub Actions run

---

## 8. Project layout

```
school-devops-python/
├─ service_students/        # Service A (FastAPI, :8001)
│  ├─ app/{data,services,controllers}/  + main.py, config.py, schemas.py
│  ├─ tests/                # repository / service / controller (respx)
│  ├─ Dockerfile
│  └─ requirements.txt
├─ service_courses/         # Service B (FastAPI, :8002)
│  ├─ app/{data,services,controllers}/  + main.py, config.py, schemas.py
│  ├─ tests/
│  ├─ Dockerfile
│  └─ requirements.txt
├─ frontend/                # nginx static dashboard (:8080)
│  ├─ index.html, styles.css, app.js, Dockerfile
├─ docker-compose.yml
├─ .github/workflows/ci.yml
├─ pyproject.toml
├─ Makefile
├─ .gitignore
└─ README.md
```
