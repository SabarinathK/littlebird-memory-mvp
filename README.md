# MemChat

MemChat is a local desktop-first memory assistant that captures on-screen context, extracts structured entities with an LLM, stores semantic memory, and lets you chat against that memory.

This repository is an MVP. It is not an official project or clone.

## Demo

[![Watch Demo](https://img.youtube.com/vi/Il4p9ZMiMw8/0.jpg)](https://youtu.be/Il4p9ZMiMw8)

## What It Does

- Captures text from the active Windows foreground app
- Ignores selected apps and sensitive-looking titles
- Stores raw events in SQLite
- Stores semantic embeddings in ChromaDB
- Extracts entities, relationships, and summaries with Groq
- Supports question answering over captured memory
- Provides `console`, `tray`, and `desktop` modes
- Includes a desktop UI built with HTML/CSS/JS inside `pywebview`

## Current Architecture

- `SQLite`
  - Raw event storage
  - Extracted entities
  - Lightweight relationship graph table
- `ChromaDB`
  - Semantic retrieval for memory search
- `Groq`
  - Entity extraction
  - Grounded answer generation
- `PyWebView`
  - Desktop shell for the local web UI

## Project Structure

```text
demo.py                  Entry script
littlebird/
  app.py                 Application bootstrap and CLI
  agent.py               Capture agent lifecycle
  capture.py             Screen capture logic
  config.py              Config and logging
  desktop.py             Desktop server, APIs, pywebview launcher
  llm.py                 Groq integration
  pipeline.py            Ingestion pipeline
  query.py               Memory retrieval and Q&A
  storage.py             SQLite + ChromaDB storage
  ui.py                  Console and tray modes
  utils.py               Shared helpers
  web/
    index.html           Desktop UI
    styles.css           Desktop styling
    app.js               Desktop frontend logic
```

## Requirements

- Windows
- Python 3.12 for source runs
- Groq API key
- The packages listed in `requirements.txt`

## Setup

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

## Running The App

### Console Mode

```powershell
py demo.py
```

### Tray Mode

```powershell
py demo.py --mode tray
```

### Desktop Mode

```powershell
py demo.py --mode desktop
```

### Useful Flags

```powershell
py demo.py --no-seed
py demo.py --quiet
py demo.py --mode desktop --no-seed
```

## Desktop Mode

Desktop mode opens a local UI in `pywebview`.

The current UI includes:

- Capture status
- Start / Pause / Stop controls
- Chat interface for asking memory questions

The frontend branding currently uses `MemChat`.

## Local Desktop API

Desktop mode starts a local HTTP server for the frontend.

Available endpoints:

- `GET /api/status`
- `GET /api/recent`
- `POST /api/capture/start`
- `POST /api/capture/pause`
- `POST /api/capture/stop`
- `POST /api/chat`

Example chat request:

```json
{
  "question": "What was I researching in the browser?"
}
```

## How Memory Works

1. The active foreground window is read using Windows UI Automation when available.
2. The captured text is stored as a raw event in SQLite.
3. Groq extracts:
   - entities
   - relationships
   - a one-line summary
4. A semantic embedding is generated and stored in ChromaDB.
5. When you ask a question, the system combines:
   - vector similarity
   - entity matches
   - graph relationships
6. Groq generates an answer grounded in the retrieved context.

## Notes About Capture Behavior

- Repeated identical screen captures are deduplicated
- Some apps and titles are ignored based on config
- If the screen appears to "freeze" after one capture, the most common reason is duplicate suppression, not a dead thread

## Configuration

Runtime config lives in `littlebird/config.py`.

Important values include:

- `groq_model`
- `screen_poll_interval`
- `db_path`
- `collection_name`
- `embedding_model`
- `ignored_apps`
- `ignored_titles`

## Packaging Notes

The desktop app can be packaged with PyInstaller, but there is currently a blocker:

- `sentence-transformers` pulls in `scikit-learn` and `scipy`
- packaged builds on Python 3.12 currently fail in frozen mode with a SciPy import error

Observed packaged error:

```text
NameError: name 'obj' is not defined
```

Recommended workaround:

- package using Python 3.11 instead of Python 3.12

Example build command:

```powershell
python -m PyInstaller --noconfirm --clean --name MemChat --onedir --add-data "littlebird\web;littlebird\web" demo.py
```

## Known Limitations

- Windows-first implementation
- UI Automation quality depends on the target app
- Entity extraction quality depends on model responses
- Graph storage is currently lightweight and SQL-backed, not a dedicated graph database
- First embedding model load may download files from Hugging Face
- Frozen `.exe` packaging is not reliable on Python 3.12 because of the SciPy issue above

## Suggested Next Improvements

- Better entity resolution and graph reasoning
- Smarter deduplication and capture visibility
- More robust packaging strategy
- Improved desktop app polish and settings
- Optional real graph database for deeper relationship traversal

## License / Status

MVP research project for local memory capture and retrieval experiments.
