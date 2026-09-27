PYTHON ?= python

.PHONY: run-dev playground playground-dev docker-build docker-up docker-down test lint test-integration

run-dev:
	$(PYTHON) -m app.main

playground:
	cd playground && bun install --frozen-lockfile && bun run build

playground-dev:
	cd playground && bun install --frozen-lockfile && bun run dev

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

test:
	$(PYTHON) -m pytest -q -m "not integration"

lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .

test-integration:
	$(PYTHON) -m pytest -q -m integration
