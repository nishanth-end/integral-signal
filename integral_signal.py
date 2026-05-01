import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import difflib
import os

def fetch_content(url):
    response = requests.get(url, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')
    for tag in soup(['script', 'style']):
        tag.decompose()
    return soup.get_text(separator=' ', strip=True)

def load_snapshots():
    if os.path.exists('snapshots.json'):
        with open('snapshots.json', 'r') as f:
            return json.load(f)
    return {}

def save_snapshot(url, content):
    snapshots = load_snapshots()
    snapshots[url] = {
        'content': content,
        'timestamp': datetime.now().isoformat()
    }
    with open('snapshots.json', 'w') as f:
        json.dump(snapshots, f, indent=2)
    print(f"Snapshot saved for {url}")

def compare_snapshots(url):
    snapshots = load_snapshots()
    if url not in snapshots:
        print("No previous snapshot found. Saving first snapshot.")
        content = fetch_content(url)
        save_snapshot(url, content)
        return

    old_content = snapshots[url]['content']
    old_timestamp = snapshots[url]['timestamp']
    new_content = fetch_content(url)

    if old_content == new_content:
        print(f"No changes detected since {old_timestamp}")
        return

    diff = difflib.unified_diff(
        old_content.splitlines(),
        new_content.splitlines(),
        lineterm='',
        n=3
    )

    print(f"Changes detected since {old_timestamp}:")
    for line in diff:
        print(line)

    save_snapshot(url, new_content)

def main():
    print("=== Integral Signal ===")
    url = input("Enter citation URL to check: ").strip()
    compare_snapshots(url)

if __name__ == "__main__":
    main()