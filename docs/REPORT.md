# DevOps Project Report — School-Service Microservices (Python)

**Course:** DevOps · **Format:** binôme · **Language:** Python 3.12
**Repository:** `school-devops-python` · **Generated:** 2026-06-22

---

## 1. Objective

Build an application that respects DevOps practices: a Git repository, a CI
pipeline, a layered software architecture (Data / Services / Controller), at
least two back-end services integrated with Docker, unit tests of every layer
including web mocks, good code coverage, and high software quality. Continuous
Delivery is explicitly out of scope.

The chosen domain is a **school management system** split into two
independent FastAPI microservices that communicate over HTTP.

---

## 2. Architecture

```
                          ┌──────────────────────────────┐
                          │         FRONTEND (SPA)        │
                          │   nginx static · :8080        │
                          └───────────┬──────────┬────────┘
                          fetch :8001 │          │ fetch :8002
                                      ▼          ▼
        ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
        │   SERVICE A — STUDENTS  :8001    │   │   SERVICE B — COURSES   :8002    │
        │   Controller (APIRouter)         │   │   Controller (APIRouter)         │
        │   Services (StudentService,      │   │   Services (CourseService)       │
        │             CoursesClient) ──────┼───┼──► GET /courses/{code}           │
        │                            ──────┼───┼──► GET /grades/{sid}/{code}      │
        │   Data (SQLAlchemy, students.db) │   │   Data (SQLAlchemy, courses.db)  │
        └─────────────────────────────────┘   └─────────────────────────────────┘
                       A  ───────────  HTTP (httpx)  ───────────►  B
```

### 2.1 Three-layer split (per service)

| Layer | Responsibility | Implementation |
|---|---|---|
| **Data** | persistence | SQLAlchemy 2.x models + repository over SQLite |
| **Services** | business logic | `StudentService` / `CourseService` (pure, DB-agnostic) |
| **Controller** | HTTP surface | FastAPI `APIRouter` with Pydantic schemas |

### 2.2 Inter-service interaction

Service A never reads Service B's database directly. When enrolling a student
or building a transcript, A's `CoursesClient` (built on `httpx`) calls B over
HTTP:

- `GET /courses/{code}` — validate that a course exists before enrollment.
- `GET /grades/{student_id}/{course_code}` — fetch a grade for the transcript.

This outbound HTTP call is the seam that is **mocked** in A's unit tests
(see §4).

---

## 3. API surface

**Service A — Students (`:8001`)**

| Method | Path | Purpose |
|---|---|---|
| POST | `/students` | create a student |
| GET | `/students` | list students |
| GET | `/students/{id}` | get one student |
| PUT | `/students/{id}` | update a student |
| DELETE | `/students/{id}` | delete a student |
| POST | `/students/{id}/enroll` | enroll (validates course via Service B) |
| GET | `/students/{id}/transcript` | transcript (pulls grades via Service B) |

**Service B — Courses & Grades (`:8002`)**

| Method | Path | Purpose |
|---|---|---|
| POST/GET/PUT/DELETE | `/courses[/{code}]` | course CRUD |
| POST/GET | `/grades` | record / list grades |
| GET | `/grades/{student_id}/{course_code}` | fetch one grade |

---

## 4. Testing strategy

Every architectural layer is tested in isolation, and the cross-service HTTP
call is mocked with **`respx`** so Service A's tests run without Service B
being up.

| Test file | Layer | What it covers |
|---|---|---|
| `service_students/tests/test_repository.py` | Data | CRUD against an in-memory SQLite session |
| `service_students/tests/test_student_service.py` | Services | enrollment / transcript logic — **B mocked with respx** |
| `service_students/tests/test_controller.py` | Controller | endpoints via FastAPI `TestClient` — **B mocked with respx** |
| `service_courses/tests/test_repository.py` | Data | course/grade CRUD |
| `service_courses/tests/test_course_service.py` | Services | course/grade business logic |
| `service_courses/tests/test_controller.py` | Controller | endpoints via `TestClient` |

Test isolation is provided by `conftest.py` fixtures that build a fresh
in-memory database and override FastAPI dependencies per test.

---

## 5. Test & coverage results

Run on 2026-06-22 (Python 3.12, `pytest --cov=app`):

| Service | Tests | Result | Coverage |
|---|---|---|---|
| **Students (A)** | 19 | ✅ all pass | **89%** |
| **Courses (B)** | 15 | ✅ all pass | **96%** |
| **Total** | **34** | ✅ all pass | both **> 80% target** |

Reproduce locally:

```bash
cd service_students && pytest --cov=app --cov-report=term-missing
cd service_courses  && pytest --cov=app --cov-report=term-missing
```

---

## 6. Code quality

| Tool | Role | Status |
|---|---|---|
| **ruff** | lint + import sorting (`E,F,I,UP,B,C4`) | ✅ "All checks passed" |
| **black** | formatting (line length 100) | configured |
| **mypy** | static typing | configured (non-blocking in CI) |
| **pytest-cov** | coverage reporting | ✅ 89% / 96% |

All tooling is centralised in `pyproject.toml`.

---

## 7. CI pipeline (GitHub Actions)

`.github/workflows/ci.yml` runs on every push and pull request:

1. Checkout + set up Python 3.12 (pip cache).
2. Install both services' requirements + dev tooling.
3. **ruff** lint.
4. **mypy** (non-blocking).
5. **pytest + coverage** for each service.
6. Upload `coverage.xml` artifacts.

---

## 8. Docker / orchestration

`docker-compose.yml` builds and wires three containers:

| Service | Image source | Port |
|---|---|---|
| `service_students` | `./service_students/Dockerfile` | 8001 |
| `service_courses` | `./service_courses/Dockerfile` | 8002 |
| `frontend` | `./frontend/Dockerfile` (nginx) | 8080 |

Service A receives Service B's URL through the `COURSES_SERVICE_URL`
environment variable, so the two communicate by container name on the compose
network. Bring the stack up with `docker compose up --build`.

---

## 9. Requirement coverage checklist

| Requirement | Status |
|---|---|
| Dépôt Git | ✅ repo initialised, conventional commit |
| Pipeline CI | ✅ GitHub Actions (ruff → mypy → pytest → coverage) |
| Couches Data / Services / Controller | ✅ enforced in both services |
| ≥ 2 back services + Docker | ✅ two FastAPI services in docker-compose |
| Tests unitaires (toutes couches) | ✅ 34 tests, one suite per layer |
| Mocks web | ✅ `respx` mocks the A→B HTTP call |
| Bonne couverture | ✅ 89% / 96% (target ≥ 80%) |
| Qualité logicielle | ✅ ruff + black + mypy + coverage |
| Pas de Continuous Delivery | ✅ none added (out of scope) |
| Bonus — Base de données | ✅ SQLite via SQLAlchemy |
| Bonus — Front Web | ✅ vanilla-JS dashboard |

---

## 10. Remaining / submission notes

- **Push to GitHub** to trigger the CI run, then capture the green pipeline +
  coverage artifact screenshots for the written report.
- Add the **Google Cloud labs screenshots** required by the brief.
- Submit on Moodle.
