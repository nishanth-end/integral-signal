import difflib
from fastapi import FastAPI, Request, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sys
import os
import threading
import time

try:
    import backend.snapshot as snapshot
    import backend.storage as storage
except ImportError:
    import snapshot
    import storage

# Automatically exit if parent process terminates
def _watch_parent():
    initial_ppid = os.getppid()
    while True:
        time.sleep(2)
        current_ppid = os.getppid()
        if current_ppid != initial_ppid or current_ppid <= 1:
            os._exit(0)

_parent_watcher = threading.Thread(target=_watch_parent, daemon=True)
_parent_watcher.start()

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

class ArticleCreatePayload(BaseModel):
    title: str

class ArticleUpdatePayload(BaseModel):
    title: str

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

# --- Articles Endpoints ---

@app.post("/articles")
def create_article_endpoint(payload: ArticleCreatePayload):
    try:
        created = storage.create_article(payload.title)
        return created
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.get("/articles")
def list_articles():
    articles = storage.get_all_articles()
    return {
        "count": len(articles),
        "articles": articles
    }

@app.get("/articles/{article_id}")
def get_article_endpoint(article_id: int):
    article = storage.get_article(article_id)
    if not article:
        return JSONResponse(status_code=404, content={"error": f"Article {article_id} not found"})
    return article

@app.get("/articles/{article_id}/sources")
def get_article_sources(article_id: int):
    try:
        sources = storage.get_sources_for_article(article_id)
        return {
            "article_id": article_id,
            "count": len(sources),
            "sources": sources
        }
    except ValueError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})

@app.post("/articles/{article_id}/sources")
def add_article_source(article_id: int, payload: URLPayload):
    article = storage.get_article(article_id)
    if not article:
        return JSONResponse(status_code=404, content={"error": f"Article {article_id} not found"})

    # Fetch snapshot content and save snapshot record
    content = snapshot.fetch_content(payload.url)
    saved = storage.save_snapshot(payload.url, content, trigger="manual")
    link = storage.link_source_to_article(article_id, payload.url)

    return {
        "status": "ok",
        "article_id": article_id,
        "source_id": saved["source_id"],
        "url": saved["url"],
        "snapshot_id": saved["id"],
        "timestamp": saved["fetched_at"],
        "content_hash": saved["content_hash"],
        "linked_at": link["created_at"]
    }

@app.delete("/articles/{article_id}/sources/{source_id}")
def unlink_article_source(article_id: int, source_id: int):
    article = storage.get_article(article_id)
    if not article:
        return JSONResponse(status_code=404, content={"error": f"Article {article_id} not found"})

    unlinked = storage.unlink_source_from_article(article_id, source_id)
    if not unlinked:
        return JSONResponse(status_code=404, content={"error": f"Source {source_id} is not linked to article {article_id}"})

    return {
        "status": "ok",
        "message": f"Source {source_id} unlinked from article {article_id}"
    }

@app.patch("/articles/{article_id}")
def update_article_endpoint(article_id: int, payload: ArticleUpdatePayload):
    try:
        updated = storage.update_article(article_id, payload.title)
        if not updated:
            return JSONResponse(status_code=404, content={"error": f"Article {article_id} not found"})
        return updated
    except ValueError as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.delete("/articles/{article_id}")
def delete_article_endpoint(article_id: int):
    deleted = storage.delete_article(article_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"error": f"Article {article_id} not found"})
    return {
        "status": "ok",
        "message": f"Article {article_id} deleted"
    }

@app.delete("/sources/{source_id}")
def delete_source_endpoint(source_id: int):
    deleted = storage.delete_source(source_id)
    if not deleted:
        return JSONResponse(status_code=404, content={"error": f"Source {source_id} not found"})
    return {
        "status": "ok",
        "message": f"Source {source_id} and all its snapshot history deleted permanently"
    }



if __name__ == "__main__":
    import uvicorn
    storage.init_db()
    uvicorn.run(app, host="127.0.0.1", port=8765)


