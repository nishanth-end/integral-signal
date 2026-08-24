import sqlite3
import hashlib
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

# Locate data directory relative to repository root
DEFAULT_DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "integral-signal.db"
)

def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    # Strictly enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: Optional[str] = None):
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                fetched_at TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                trigger TEXT NOT NULL DEFAULT 'manual',
                FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_source_id ON snapshots(source_id);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_fetched_at ON snapshots(fetched_at);
        """)
        conn.commit()

def get_or_create_source(conn: sqlite3.Connection, url: str) -> int:
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM sources WHERE url = ?", (url,))
    row = cursor.fetchone()
    if row:
        return row["id"]
    
    now = datetime.now().isoformat()
    cursor.execute("INSERT INTO sources (url, created_at) VALUES (?, ?)", (url, now))
    return cursor.lastrowid

def save_snapshot(
    url: str,
    content: str,
    trigger: str = "manual",
    db_path: Optional[str] = None
) -> Dict[str, Any]:
    content_hash = compute_hash(content)
    now = datetime.now().isoformat()

    with get_connection(db_path) as conn:
        source_id = get_or_create_source(conn, url)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO snapshots (source_id, content, fetched_at, content_hash, trigger)
            VALUES (?, ?, ?, ?, ?)
            """,
            (source_id, content, now, content_hash, trigger)
        )
        snapshot_id = cursor.lastrowid
        conn.commit()

        return {
            "id": snapshot_id,
            "source_id": source_id,
            "url": url,
            "content": content,
            "fetched_at": now,
            "content_hash": content_hash,
            "trigger": trigger
        }

def get_latest_snapshot(url: str, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.id, s.source_id, src.url, s.content, s.fetched_at, s.content_hash, s.trigger
            FROM snapshots s
            JOIN sources src ON s.source_id = src.id
            WHERE src.url = ?
            ORDER BY s.fetched_at DESC, s.id DESC
            LIMIT 1
            """,
            (url,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

def get_snapshot_history(url: str, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT s.id, s.source_id, src.url, s.content, s.fetched_at, s.content_hash, s.trigger
            FROM snapshots s
            JOIN sources src ON s.source_id = src.id
            WHERE src.url = ?
            ORDER BY s.fetched_at DESC, s.id DESC
            """,
            (url,)
        )
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_all_sources(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, url, created_at FROM sources ORDER BY created_at DESC;")
        source_rows = cursor.fetchall()

        results = []
        for s in source_rows:
            source_id = s["id"]
            url = s["url"]

            # Get the two most recent snapshots to determine status
            cursor.execute(
                """
                SELECT id, fetched_at, content_hash, trigger
                FROM snapshots
                WHERE source_id = ?
                ORDER BY fetched_at DESC, id DESC
                LIMIT 2;
                """,
                (source_id,)
            )
            recent_snaps = cursor.fetchall()

            # Get total snapshot count
            cursor.execute("SELECT COUNT(*) as cnt FROM snapshots WHERE source_id = ?;", (source_id,))
            cnt_row = cursor.fetchone()
            total_count = cnt_row["cnt"] if cnt_row else 0

            # Only include sources that have at least one snapshot
            if total_count == 0:
                continue

            last_snapshot = recent_snaps[0]
            last_checked = last_snapshot["fetched_at"]

            if len(recent_snaps) >= 2:
                latest_hash = recent_snaps[0]["content_hash"]
                prev_hash = recent_snaps[1]["content_hash"]
                status = "changed" if latest_hash != prev_hash else "no_change"
            else:
                status = "initial"

            results.append({
                "id": source_id,
                "url": url,
                "created_at": s["created_at"],
                "last_checked": last_checked,
                "snapshot_count": total_count,
                "status": status,
                "latest_hash": last_snapshot["content_hash"]
            })

        # Sort by most recently checked
        results.sort(key=lambda x: x["last_checked"], reverse=True)
        return results

