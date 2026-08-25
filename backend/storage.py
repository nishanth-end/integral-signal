import sqlite3
import hashlib
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

import sys

# Locate data directory relative to repository root or macOS Application Support when frozen
def get_default_db_path() -> str:
    if os.environ.get("INTEGRAL_SIGNAL_DB_PATH"):
        return os.environ["INTEGRAL_SIGNAL_DB_PATH"]
    if getattr(sys, "frozen", False):
        app_dir = os.path.expanduser("~/Library/Application Support/Integral Signal")
        os.makedirs(app_dir, exist_ok=True)
        return os.path.join(app_dir, "integral-signal.db")
    
    # Dev mode: relative to repo root
    repo_data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data"
    )
    os.makedirs(repo_data_dir, exist_ok=True)
    return os.path.join(repo_data_dir, "integral-signal.db")

def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = db_path or get_default_db_path()
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
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS article_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                source_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
                FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE,
                UNIQUE(article_id, source_id)
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_source_id ON snapshots(source_id);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_snapshots_fetched_at ON snapshots(fetched_at);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_article_sources_article_id ON article_sources(article_id);
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_article_sources_source_id ON article_sources(source_id);
        """)
        conn.commit()

        # Automatic migration: link any unlinked legacy sources to a "Legacy Sources" article
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM sources
            WHERE id NOT IN (SELECT DISTINCT source_id FROM article_sources);
        """)
        unlinked_rows = cursor.fetchall()
        if unlinked_rows:
            now = datetime.now().isoformat()
            cursor.execute("SELECT id FROM articles WHERE title = ?", ("Legacy Sources",))
            legacy_row = cursor.fetchone()
            if legacy_row:
                legacy_article_id = legacy_row["id"]
            else:
                cursor.execute(
                    "INSERT INTO articles (title, created_at) VALUES (?, ?)",
                    ("Legacy Sources", now)
                )
                legacy_article_id = cursor.lastrowid
            
            for row in unlinked_rows:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO article_sources (article_id, source_id, created_at)
                    VALUES (?, ?, ?)
                    """,
                    (legacy_article_id, row["id"], now)
                )
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

def create_article(title: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    now = datetime.now().isoformat()
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("Article title cannot be empty")

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO articles (title, created_at) VALUES (?, ?)",
            (clean_title, now)
        )
        article_id = cursor.lastrowid
        conn.commit()
        return {
            "id": article_id,
            "title": clean_title,
            "created_at": now,
            "source_count": 0
        }

def get_all_articles(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                a.id, 
                a.title, 
                a.created_at,
                COUNT(ars.id) as source_count
            FROM articles a
            LEFT JOIN article_sources ars ON a.id = ars.article_id
            GROUP BY a.id
            ORDER BY a.created_at DESC, a.id DESC
        """)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_article(article_id: int, db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                a.id, 
                a.title, 
                a.created_at,
                COUNT(ars.id) as source_count
            FROM articles a
            LEFT JOIN article_sources ars ON a.id = ars.article_id
            WHERE a.id = ?
            GROUP BY a.id
        """, (article_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return dict(row)

def link_source_to_article(article_id: int, url: str, db_path: Optional[str] = None) -> Dict[str, Any]:
    now = datetime.now().isoformat()
    clean_url = url.strip()
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Verify article exists
        cursor.execute("SELECT id FROM articles WHERE id = ?", (article_id,))
        if not cursor.fetchone():
            raise ValueError(f"Article with id {article_id} not found")

        source_id = get_or_create_source(conn, clean_url)
        cursor.execute(
            """
            INSERT OR IGNORE INTO article_sources (article_id, source_id, created_at)
            VALUES (?, ?, ?)
            """,
            (article_id, source_id, now)
        )
        conn.commit()
        return {
            "article_id": article_id,
            "source_id": source_id,
            "url": clean_url,
            "created_at": now
        }

def get_sources_for_article(article_id: int, db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        # Check if article exists
        cursor.execute("SELECT id FROM articles WHERE id = ?", (article_id,))
        if not cursor.fetchone():
            raise ValueError(f"Article with id {article_id} not found")

        cursor.execute("""
            SELECT s.id, s.url, s.created_at, ars.created_at as linked_at
            FROM sources s
            JOIN article_sources ars ON s.id = ars.source_id
            WHERE ars.article_id = ?
            ORDER BY ars.created_at DESC, s.id DESC
        """, (article_id,))
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

            if total_count > 0:
                last_snapshot = recent_snaps[0]
                last_checked = last_snapshot["fetched_at"]
                latest_hash = last_snapshot["content_hash"]

                if len(recent_snaps) >= 2:
                    status = "changed" if recent_snaps[0]["content_hash"] != recent_snaps[1]["content_hash"] else "no_change"
                else:
                    status = "initial"
            else:
                last_checked = None
                latest_hash = None
                status = "initial"

            results.append({
                "id": source_id,
                "url": url,
                "created_at": s["created_at"],
                "linked_at": s["linked_at"],
                "last_checked": last_checked,
                "snapshot_count": total_count,
                "status": status,
                "latest_hash": latest_hash
            })

        # Sort by most recently checked, or linked date
        results.sort(key=lambda x: x["last_checked"] or x["linked_at"] or "", reverse=True)
        return results

def unlink_source_from_article(article_id: int, source_id: int, db_path: Optional[str] = None) -> bool:
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM article_sources WHERE article_id = ? AND source_id = ?",
            (article_id, source_id)
        )
        conn.commit()
        return cursor.rowcount > 0


