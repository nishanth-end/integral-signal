import difflib
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import backend.snapshot as snapshot
import backend.storage as storage

app = FastAPI(title="Integral Signal Backend", version="0.0.1")

# Allow CORS for Tauri and frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class URLPayload(BaseModel):
    url: str

@app.on_event("startup")
def on_startup():
    storage.init_db()

@app.exception_handler(snapshot.FetchError)
async def fetch_error_handler(request: Request, exc: snapshot.FetchError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.message,
            "status_code": exc.status_code,
            "detail": exc.detail
        }
    )

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/version")
def version():
    return {"version": "0.0.1"}

@app.post("/sources/snapshot")
def create_snapshot(payload: URLPayload):
    content = snapshot.fetch_content(payload.url)
    saved = storage.save_snapshot(payload.url, content, trigger="manual")
    return {
        "status": "ok",
        "id": saved["id"],
        "url": saved["url"],
        "timestamp": saved["fetched_at"],
        "content": saved["content"],
        "content_hash": saved["content_hash"],
        "trigger": saved["trigger"]
    }

@app.post("/sources/diff")
def diff_snapshot(payload: URLPayload):
    latest = storage.get_latest_snapshot(payload.url)
    if not latest:
        return {
            "status": "no_prior_snapshot",
            "url": payload.url,
            "message": "No existing snapshot found for this URL. Take a snapshot first."
        }

    new_content = snapshot.fetch_content(payload.url)
    new_hash = storage.compute_hash(new_content)

    # Fast hash comparison
    if latest["content_hash"] == new_hash:
        return {
            "status": "no_change",
            "url": payload.url,
            "timestamp": latest["fetched_at"],
            "message": f"No changes detected since snapshot at {latest['fetched_at']}"
        }

    # If content changed, compute line-by-line diff and record new snapshot
    diff = list(difflib.unified_diff(
        latest["content"].splitlines(),
        new_content.splitlines(),
        lineterm='',
        n=3
    ))

    saved = storage.save_snapshot(payload.url, new_content, trigger="diff_check")
    return {
        "status": "changes_detected",
        "url": payload.url,
        "previous_timestamp": latest["fetched_at"],
        "current_timestamp": saved["fetched_at"],
        "diff": diff
    }

@app.get("/sources")
def list_sources():
    sources = storage.get_all_sources()
    return {
        "count": len(sources),
        "sources": sources
    }

@app.get("/sources/history")
def get_history(url: str = Query(..., description="Target source URL")):
    history = storage.get_snapshot_history(url)
    return {
        "url": url,
        "count": len(history),
        "history": history
    }


if __name__ == "__main__":
    import uvicorn
    storage.init_db()
    uvicorn.run(app, host="127.0.0.1", port=8765)


