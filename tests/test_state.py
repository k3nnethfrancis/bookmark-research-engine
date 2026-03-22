"""Tests for bre.state — dedup and persistence."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bre.state import (
    get_archived_ids,
    load_pending,
    load_state,
    merge_pending,
    save_pending,
    save_state,
)


# ── load_state / save_state ──────────────────────────────────────────────

class TestState:
    def test_load_missing(self, tmp_path):
        state = load_state(tmp_path / "nonexistent.json")
        assert state["last_check"] is None
        assert state["last_processed_id"] is None

    def test_roundtrip(self, tmp_path):
        path = tmp_path / "state.json"
        state = {"last_check": "2026-03-21T00:00:00", "last_processed_id": "123"}
        save_state(path, state)
        loaded = load_state(path)
        assert loaded["last_check"] == "2026-03-21T00:00:00"
        assert loaded["last_processed_id"] == "123"

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "state.json"
        save_state(path, {"last_check": None})
        assert path.exists()


# ── load_pending / save_pending ──────────────────────────────────────────

class TestPending:
    def test_load_missing(self, tmp_path):
        pending = load_pending(tmp_path / "nonexistent.json")
        assert pending["bookmarks"] == []
        assert pending["count"] == 0

    def test_roundtrip(self, tmp_path):
        path = tmp_path / "pending.json"
        data = {"bookmarks": [{"id": "123", "text": "test"}], "count": 1}
        save_pending(path, data)
        loaded = load_pending(path)
        assert loaded["count"] == 1
        assert loaded["bookmarks"][0]["id"] == "123"


# ── get_archived_ids ─────────────────────────────────────────────────────

class TestArchivedIds:
    def test_extracts_ids(self, tmp_path):
        archive = tmp_path / "bookmarks.md"
        archive.write_text(
            "# Bookmarks\n"
            "- https://x.com/user1/status/111222333\n"
            "- https://x.com/user2/status/444555666\n"
            "- Some other text\n"
            "- https://x.com/user3/status/777888999\n"
        )
        ids = get_archived_ids(archive)
        assert ids == {"111222333", "444555666", "777888999"}

    def test_missing_file(self, tmp_path):
        ids = get_archived_ids(tmp_path / "nonexistent.md")
        assert ids == set()

    def test_no_matches(self, tmp_path):
        archive = tmp_path / "bookmarks.md"
        archive.write_text("# Bookmarks\nNo tweet links here\n")
        assert get_archived_ids(archive) == set()


# ── merge_pending ────────────────────────────────────────────────────────

class TestMergePending:
    def test_dedup(self):
        existing = [{"id": "1", "createdAt": "Wed Oct 10 20:19:24 +0000 2018"}]
        new = [
            {"id": "1", "createdAt": "Wed Oct 10 20:19:24 +0000 2018"},  # duplicate
            {"id": "2", "createdAt": "Thu Oct 11 20:19:24 +0000 2018"},
        ]
        merged = merge_pending(existing, new)
        assert len(merged) == 2
        ids = [b["id"] for b in merged]
        assert "1" in ids
        assert "2" in ids

    def test_sort_ascending(self):
        bookmarks = [
            {"id": "2", "createdAt": "Thu Oct 11 20:19:24 +0000 2018"},
            {"id": "1", "createdAt": "Wed Oct 10 20:19:24 +0000 2018"},
        ]
        merged = merge_pending([], bookmarks)
        assert merged[0]["id"] == "1"  # older first
        assert merged[1]["id"] == "2"

    def test_empty_inputs(self):
        assert merge_pending([], []) == []

    def test_missing_created_at(self):
        """Bookmarks without createdAt should sort to the front (timestamp 0)."""
        bookmarks = [
            {"id": "2", "createdAt": "Wed Oct 10 20:19:24 +0000 2018"},
            {"id": "1"},  # no createdAt
        ]
        merged = merge_pending([], bookmarks)
        assert merged[0]["id"] == "1"  # no date → timestamp 0 → first
