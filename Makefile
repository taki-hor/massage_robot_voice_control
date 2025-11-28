# Makefile for UR10e Voice-Controlled Massage System

.PHONY: install dev server ui test clean

# Install all dependencies
install:
	pip install -r requirements.txt
	cd ui && npm install

# Development mode (run both server and UI)
dev:
	@echo "Starting development servers..."
	@make server &
	@make ui

# Start FastAPI server
server:
	python run.py

# Start FastAPI server with hot reload
server-dev:
	python -m uvicorn server.main:app --reload --host 0.0.0.0 --port 8000

# Start UI development server
ui:
	cd ui && npm run dev

# Build UI for production
build-ui:
	cd ui && npm run build

# Run tests
test:
	pytest tests/ -v

# Run robot connection test
test-robot:
	python -c "from robot_control.adapter import RobotAdapter; r = RobotAdapter(); print('Connected:', r.connect())"

# Clean build artifacts
clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache
	rm -rf ui/dist ui/node_modules

# Format code
format:
	black robot_control/ voice/ server/ tests/
	cd ui && npm run lint -- --fix

# Type check
typecheck:
	mypy robot_control/ voice/ server/
