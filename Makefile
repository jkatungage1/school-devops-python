# Convenience targets for the school DevOps project.
# Usage: make install | make test | make cov | make lint | make run | make docker-up

PYTHON ?= python
PIP ?= $(PYTHON) -m pip

.PHONY: install test cov lint format run-students run-courses run docker-up docker-down clean

install:  ## install both services' deps + dev tooling
	$(PIP) install -r service_students/requirements.txt
	$(PIP) install -r service_courses/requirements.txt
	$(PIP) install -e ".[dev]"

test:  ## run unit tests for both services
	cd service_students && $(PYTHON) -m pytest
	cd service_courses && $(PYTHON) -m pytest

cov:  ## run tests with coverage for both services
	cd service_students && $(PYTHON) -m pytest --cov=app --cov-report=term-missing
	cd service_courses && $(PYTHON) -m pytest --cov=app --cov-report=term-missing

lint:  ## ruff lint both services
	$(PYTHON) -m ruff check service_students service_courses

format:  ## auto-format with black + ruff
	$(PYTHON) -m black service_students service_courses
	$(PYTHON) -m ruff check --fix service_students service_courses

run-courses:  ## run Service B locally on :8002
	cd service_courses && $(PYTHON) -m uvicorn app.main:app --reload --port 8002

run-students:  ## run Service A locally on :8001
	cd service_students && $(PYTHON) -m uvicorn app.main:app --reload --port 8001

run: docker-up  ## alias for docker-up

docker-up:  ## build + start the whole stack (students:8001 courses:8002 frontend:8080)
	docker compose up --build

docker-down:  ## stop the stack
	docker compose down

clean:  ## remove caches and local sqlite files
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov .coverage
	find . -name "__pycache__" -type d -prune -exec rm -rf {} +
	find . -name "*.db" -delete
