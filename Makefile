
.PHONY: scrape run setup

setup:
	@echo "Checking for uv..."
	@command -v uv >/dev/null 2>&1 || (echo "uv not found, installing..." && curl -LsSf https://astral.sh/uv/install.sh | sh)
	@echo "Syncing dependencies..."
	uv sync
	@echo "Setting up Ollama models..."
	ollama pull minicpm-v
	ollama pull nomic-embed-text
	@echo "Setup complete."

clean_all:
	@echo "Cleaning up database and images..."
	rm -f miniscope.db
	rm -rf data/images
	mkdir -p data/images
	@echo "Cleanup complete."

scrape:
	@echo "Running scrape..."
	uv run python -m miniscope.main scrape

run:
	@echo "Starting web server..."
	uv run uvicorn miniscope.main:app --reload
