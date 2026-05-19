.PHONY: help install backend frontend dev test test-backend test-frontend fmt lint openapi clean

help:
	@echo "Targets:"
	@echo "  install         Install backend (uv) and frontend (npm) deps"
	@echo "  dev             Run backend + frontend concurrently"
	@echo "  backend         Run backend (uvicorn --reload) on :8000"
	@echo "  frontend        Run frontend (vite) on :5173"
	@echo "  test            Run all tests"
	@echo "  test-backend    Run pytest"
	@echo "  test-frontend   Run vitest"
	@echo "  fmt             ruff format + npm format"
	@echo "  lint            ruff check + tsc"
	@echo "  openapi         Regenerate shared/openapi.json"

install:
	uv venv
	. .venv/bin/activate && uv pip install -e ".[dev]"
	cd frontend && npm install

backend:
	. .venv/bin/activate && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting backend on :8000 and frontend on :5173 (Ctrl-C stops both)"
	@trap 'kill 0' INT; \
		(. .venv/bin/activate && uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload) & \
		(cd frontend && npm run dev) & \
		wait

test: test-backend test-frontend

test-backend:
	. .venv/bin/activate && pytest -q

test-frontend:
	cd frontend && npm run test

fmt:
	. .venv/bin/activate && ruff format backend
	cd frontend && npx prettier --write "src/**/*.{ts,tsx,css}" 2>/dev/null || true

lint:
	. .venv/bin/activate && ruff check backend
	cd frontend && npx tsc -b --noEmit

openapi:
	. .venv/bin/activate && python -c "from backend.app.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > shared/openapi.json

clean:
	rm -rf .venv frontend/node_modules frontend/dist shared/openapi.json
