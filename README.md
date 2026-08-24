# Integral Signal

> A desktop tool that helps writers and journalists track when their cited web sources change or disappear.

## Why this exists

Independent journalism and research do the heavy lifting of uncovering and verifying facts, often without the institutional backing larger outlets have. But a citation is only as reliable as the source behind it, and web pages get edited, taken down, or quietly rewritten long after they've been cited. Integral Signal exists to close that gap: it lets writers and researchers know exactly what a source said when they cited it, and catch it if that changes.

This matters beyond any one article. Transparency and reliability in publicly available information are, I'd argue, a precondition for a functioning society, and tools that make that easier to maintain are worth building, even at small scale.

## What it does (current MVP)

- Add any URL to a tracked source list
- Take a snapshot of its content on demand
- Check a source for changes against its last snapshot
- View a clear, color-coded diff when content has changed
- Full snapshot history per source, persisted locally, survives app restarts

## Screenshots

NONE YET  SORRY

## Tech stack

- **Desktop shell:** Tauri (Rust)
- **Frontend:** React (Vite)
- **Backend:** Python (FastAPI), run as a local sidecar process
- **Storage:** SQLite

## Architecture

Integral Signal runs as three cooperating pieces inside one desktop app. Tauri provides the native window and, on launch, spawns a Python (FastAPI) server as a background sidecar process, listening on localhost:8765. The React frontend, running inside Tauri's webview, talks to that sidecar over plain local HTTP: it never touches SQLite or the filesystem directly. All source-tracking logic lives in the Python layer, which fetches URLs, computes a SHA-256 hash of each fetch, and compares it against the most recent stored hash to decide whether content has changed before running a full diff. Every snapshot, whether taken explicitly or triggered by a change check, is written to a local SQLite database (data/integral-signal.db), so tracked sources and their full history persist across app restarts. Tauri terminates the sidecar process when the app window closes, so nothing lingers in the background between sessions.

┌─────────────────────┐        HTTP (localhost:8765)        ┌──────────────────────┐
│   Tauri + React UI   │ ───────────────────────────────────▶│  FastAPI sidecar      │
│  (source list, diff  │◀───────────────────────────────────│  (fetch, hash, diff)  │
│   view, history)     │                                      └──────────┬───────────┘
└─────────────────────┘                                                 │
                                                                          ▼
                                                                 ┌──────────────────┐
                                                                 │  SQLite (local)   │
                                                                 │  sources /        │
                                                                 │  snapshots        │
                                                                 └──────────────────┘

## Getting started

### Prerequisites

- Node.js 
- Python 
- Rust + Tauri CLI ([install guide](https://tauri.app/start/prerequisites/))

### Backend setup

```bash
cd backend
python -m venv venv
source venv/bin/activate   # on Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend setup

```bash
cd frontend
npm install
```

### Run the app

```bash
npm run tauri dev
```


## Roadmap

- [ ] Article editor with git-style version log
- [ ] AI-assisted change flagging (user choice of local or cloud models)
- [ ] Packaged, distributable builds (Windows / Linux / macOS)


## Status

This is an early-stage personal MVP, actively under development, not production-hardened. Expect rough edges.

## License
GNU GPL 3.0 License, Look at LICENSE for more details
