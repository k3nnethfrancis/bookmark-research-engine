"""Dedup state management and pending bookmark persistence.

Port of smaug's state tracking — keeps track of last check time, manages the
pending bookmarks JSON file, and scans the archive file for already-processed IDs.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def load_state(path: Path) -> dict:
    """Load processing state from disk."""
    try:
        return json.loads(path.read_text())
    except Exception:
        return {"last_processed_id": None, "last_check": None, "last_processing_run": None}


def save_state(path: Path, state: dict):
    """Save processing state to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n")


def load_pending(path: Path) -> dict:
    """Load pending bookmarks JSON. Returns {bookmarks: [], count: 0} on missing/error."""
    try:
        data = json.loads(path.read_text())
        return {"bookmarks": data.get("bookmarks", []), "count": data.get("count", 0)}
    except Exception:
        return {"bookmarks": [], "count": 0}


def save_pending(path: Path, pending: dict):
    """Save pending bookmarks JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(pending, indent=2) + "\n")


def get_archived_ids(archive_file: Path) -> set[str]:
    """Scan archive file for tweet IDs that have already been processed.

    Looks for x.com/*/status/{id} patterns in the archive markdown.
    """
    try:
        content = archive_file.read_text()
        matches = re.findall(r"x\.com/\w+/status/(\d+)", content)
        return set(matches)
    except Exception:
        return set()


def merge_pending(
    existing: list[dict], new: list[dict]
) -> list[dict]:
    """Merge new bookmarks into existing pending list.

    - Deduplicates by ID
    - Sorts by createdAt ascending (oldest first), matching smaug behavior
    """
    seen = {str(b["id"]) for b in existing}
    merged = list(existing)

    for bookmark in new:
        bid = str(bookmark["id"])
        if bid not in seen:
            seen.add(bid)
            merged.append(bookmark)

    # Sort oldest first — when processed, oldest get added first, newest on top
    merged.sort(key=_created_at_key)
    return merged


def _created_at_key(bookmark: dict) -> float:
    """Parse createdAt for sorting. Returns 0 for unparseable dates."""
    created = bookmark.get("createdAt", "")
    if not created:
        return 0.0
    try:
        # X's date format: "Wed Oct 10 20:19:24 +0000 2018"
        dt = datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y")
        return dt.timestamp()
    except Exception:
        return 0.0
