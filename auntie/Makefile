.PHONY: setup test run clean lint format

# Setup development environment
setup:
	uv sync
	cp .env.example .env
	@echo "Setup complete! Edit .env with your configuration."

# Run all tests
test:
	uv run pytest

# Run tests with coverage
test-cov:
	uv run pytest --cov=auntie --cov-report=html

# Run the bot
run:
	uv run python -m auntie

# Clean build artifacts
clean:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf dist/
	rm -rf build/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

# Lint code
lint:
	uv run ruff check .

# Format code
format:
	uv run ruff format .
	uv run ruff check --fix .

# Type check (if mypy is added later)
type-check:
	uv run mypy auntie/
