import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import difflib
import os

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

# In-memory storage for current phase (before SQLite)
MEMORY_SNAPSHOTS: dict = {}

class FetchError(Exception):
    def __init__(self, message: str, status_code: int = 400, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail

def fetch_content(url: str, timeout: int = 10, user_agent: str = DEFAULT_USER_AGENT) -> str:
    if not url.startswith(("http://", "https://")):
        raise FetchError(
            message="Invalid URL scheme. Must start with http:// or https://",
            status_code=400,
            detail=f"Provided URL: {url}"
        )

    headers = {"User-Agent": user_agent}

    try:
        response = requests.get(url, headers=headers, timeout=timeout)
    except requests.exceptions.Timeout:
        raise FetchError(
            message=f"Request timed out after {timeout} seconds",
            status_code=504,
            detail=f"Target URL: {url}"
        )
    except requests.exceptions.ConnectionError as e:
        raise FetchError(
            message="Failed to connect to host. URL may be unreachable or invalid.",
            status_code=502,
            detail=str(e)
        )
    except requests.exceptions.RequestException as e:
        raise FetchError(
            message=f"Request failed: {str(e)}",
            status_code=502,
            detail=str(e)
        )

    if response.status_code >= 400:
        raise FetchError(
            message=f"Remote server returned HTTP {response.status_code}",
            status_code=response.status_code,
            detail=response.text[:200]
        )

    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup(['script', 'style', 'noscript']):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)

# In-memory snapshot helpers
def save_snapshot_memory(url: str, content: str) -> dict:
    snapshot_data = {
        'url': url,
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    MEMORY_SNAPSHOTS[url] = snapshot_data
    return snapshot_data

def get_snapshot_memory(url: str) -> dict:
    return MEMORY_SNAPSHOTS.get(url)

def diff_snapshots_memory(url: str, new_content: str) -> dict:
    prior = get_snapshot_memory(url)
    if not prior:
        return {
            'status': 'no_prior_snapshot',
            'url': url,
            'message': 'No existing snapshot found for this URL. Snapshot first.'
        }

    old_content = prior['content']
    old_timestamp = prior['timestamp']

    if old_content == new_content:
        return {
            'status': 'no_change',
            'url': url,
            'timestamp': old_timestamp,
            'message': f"No changes detected since snapshot at {old_timestamp}"
        }

    diff = list(difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        lineterm='',
        n=3
    ))

    # Update in-memory snapshot with latest content and return diff
    save_snapshot_memory(url, new_content)
    return {
        'status': 'changes_detected',
        'url': url,
        'previous_timestamp': old_timestamp,
        'current_timestamp': datetime.now().isoformat(),
        'diff': diff
    }

# File-based legacy helpers (preserved)
def load_snapshots(storage_path: str = 'snapshots.json') -> dict:
    if os.path.exists(storage_path):
        with open(storage_path, 'r') as f:
            return json.load(f)
    return {}

def save_snapshot(url: str, content: str, storage_path: str = 'snapshots.json') -> dict:
    snapshots = load_snapshots(storage_path)
    snapshot_data = {
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    snapshots[url] = snapshot_data
    with open(storage_path, 'w') as f:
        json.dump(snapshots, f, indent=2)
    return snapshot_data

def compare_snapshots(url: str, storage_path: str = 'snapshots.json'):
    snapshots = load_snapshots(storage_path)
    if url not in snapshots:
        content = fetch_content(url)
        save_snapshot(url, content, storage_path)
        return {
            'status': 'initial_snapshot_created',
            'url': url
        }

    old_content = snapshots[url]['content']
    old_timestamp = snapshots[url]['timestamp']
    new_content = fetch_content(url)

    if old_content == new_content:
        return {
            'status': 'no_changes',
            'timestamp': old_timestamp,
            'url': url
        }

    diff = list(difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        lineterm='',
        n=3
    ))

    save_snapshot(url, new_content, storage_path)
    return {
        'status': 'changes_detected',
        'previous_timestamp': old_timestamp,
        'diff': diff,
        'url': url
    }

