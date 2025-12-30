# Miniscope 🕵️‍♂️

Miniscope is an AI-powered search engine and database for tabletop miniatures. It scrapes miniature data, uses local vision models (via Ollama) to generate hyper-detailed physical descriptions, and provides a hybrid search interface to help you find exactly the miniature you need for your campaign.

## 🚀 Features

- **Automated Scraping**: Crawls miniature galleries (currently optimized for MinisGallery) to build a local library of metadata and images.
- **AI Vision Analysis**: Uses state-of-the-art local vision models (**MiniCPM-V** or **Llama 3.2 Vision**) to describe miniatures—identifying precisely what they are wearing and holding (swords, shields, polearms, etc.).
- **Hybrid Search Engine**:
    - **Keyword Search**: Quick SQL-based word boundary matching.
    - **Vector Search**: Semantic similarity using **Nomic Embeddings**.
    - **Smart Ranking**: Implements a semantic penalty for "near-misses" (e.g., finding an "Archon" when you searched for "Archer") and boosts results with exact keyword matches.
- **Robust Maintenance**: Tools to re-analyze descriptions, fix AI hallucinations, and recover missing images.

## 🛠 Setup

### Prerequisites

1.  **Ollama**: Ensure [Ollama](https://ollama.ai/) is installed and running on your system.
2.  **Python 3.12+**: Managed via `uv`.

### Installation

1.  **Clone and Install Dependencies**:
    ```bash
    uv sync
    ```

2.  **Initialize Models**:
    Run the setup command to pull the required AI models (MiniCPM-V and Nomic-Embed-Text):
    ```bash
    make setup
    ```

3.  **Environment Variables**:
    Create a `.env` file (or use the provided defaults in `miniscope/config.py`):
    ```env
    VISION_MODEL=minicpm-v
    EMBEDDING_MODEL=nomic-embed-text
    OLLAMA_HOST=http://localhost:11434
    ```

## 🎮 Usage

### 1. Scrape Data
To build your database, run the scraper. This will download images, generate AI descriptions, and create search embeddings.
```bash
make scrape
```

### 2. Run the Web Server
Launch the FastAPI development server:
```bash
make run
```
Access the UI at `http://localhost:8000`.

### 3. Maintenance Utilities
Maintenance scripts are located in the `utils/` directory. Run them using `uv run`:

- **Re-analyze All**: Re-run AI analysis on the entire collection (useful after changing prompts).
  ```bash
  uv run utils/reanalyze_all.py [--force]
  ```
- **Fetch Missing Images**: Re-download any images missing from the `data/images` folder.
  ```bash
  uv run utils/fetch_missing_images.py
  ```
- **Debug Search**: Test the search scoring logic from the CLI.
  ```bash
  uv run utils/debug_search.py "your query"
  ```

## 🏗 Architecture

- **Backend**: FastAPI (Python)
- **Database**: SQLite with JSON support for embeddings
- **AI**: Ollama (Local LLM/Vision API)
- **Frontend**: Vanilla HTML/JS with partials and a modern, responsive UI.

## 📝 License

This project is licensed under the [MIT License](LICENSE).

