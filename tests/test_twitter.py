"""Tests for bre.twitter — X GraphQL client."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from bre.twitter import (
    FALLBACK_QUERY_IDS,
    TwitterClient,
    extract_cursor,
    parse_timeline_instructions,
    parse_tweet_result,
)
from bre.config import TwitterAuth


# ── Fixtures ─────────────────────────────────────────────────────────────

SAMPLE_TWEET_RESULT = {
    "__typename": "Tweet",
    "rest_id": "1234567890",
    "core": {
        "user_results": {
            "result": {
                "legacy": {
                    "screen_name": "testuser",
                    "name": "Test User",
                }
            }
        }
    },
    "legacy": {
        "full_text": "This is a test tweet https://t.co/abc123",
        "created_at": "Wed Oct 10 20:19:24 +0000 2018",
        "id_str": "1234567890",
        "in_reply_to_status_id_str": None,
        "extended_entities": {
            "media": [
                {
                    "type": "photo",
                    "media_url_https": "https://pbs.twimg.com/media/test.jpg",
                    "expanded_url": "https://x.com/testuser/status/1234567890/photo/1",
                }
            ]
        },
    },
}

SAMPLE_TIMELINE_INSTRUCTIONS = [
    {
        "type": "TimelineAddEntries",
        "entries": [
            {
                "content": {
                    "entryType": "TimelineTimelineItem",
                    "itemContent": {
                        "tweet_results": {"result": SAMPLE_TWEET_RESULT}
                    },
                }
            },
            {
                "content": {
                    "cursorType": "Bottom",
                    "value": "cursor_abc123",
                }
            },
        ],
    }
]


# ── parse_tweet_result ───────────────────────────────────────────────────

class TestParseTweetResult:
    def test_basic_tweet(self):
        result = parse_tweet_result(SAMPLE_TWEET_RESULT)
        assert result is not None
        assert result["id"] == "1234567890"
        assert result["text"] == "This is a test tweet https://t.co/abc123"
        assert result["author"]["username"] == "testuser"
        assert result["author"]["name"] == "Test User"
        assert result["createdAt"] == "Wed Oct 10 20:19:24 +0000 2018"
        assert result["inReplyToStatusId"] is None
        assert result["quotedTweet"] is None
        assert len(result["media"]) == 1

    def test_empty_result(self):
        assert parse_tweet_result({}) is None
        assert parse_tweet_result(None) is None

    def test_tombstone(self):
        assert parse_tweet_result({"__typename": "TweetTombstone"}) is None

    def test_visibility_wrapper(self):
        wrapped = {
            "__typename": "TweetWithVisibilityResults",
            "tweet": SAMPLE_TWEET_RESULT,
        }
        result = parse_tweet_result(wrapped)
        assert result is not None
        assert result["id"] == "1234567890"

    def test_quoted_tweet(self):
        qt_result = {
            **SAMPLE_TWEET_RESULT,
            "rest_id": "9999999999",
            "legacy": {
                **SAMPLE_TWEET_RESULT["legacy"],
                "id_str": "9999999999",
                "full_text": "I am the quoted tweet",
            },
        }
        tweet_with_quote = {
            **SAMPLE_TWEET_RESULT,
            "quoted_status_result": {"result": qt_result},
        }
        result = parse_tweet_result(tweet_with_quote)
        assert result["quotedTweet"] is not None
        assert result["quotedTweet"]["id"] == "9999999999"
        assert result["quotedTweet"]["text"] == "I am the quoted tweet"


# ── parse_timeline_instructions ──────────────────────────────────────────

class TestParseTimelineInstructions:
    def test_basic_instructions(self):
        tweets = parse_timeline_instructions(SAMPLE_TIMELINE_INSTRUCTIONS)
        assert len(tweets) == 1
        assert tweets[0]["id"] == "1234567890"

    def test_empty_instructions(self):
        assert parse_timeline_instructions([]) == []

    def test_module_items(self):
        """Test timeline module entries (used in some timeline views)."""
        instructions = [
            {
                "type": "TimelineAddEntries",
                "entries": [
                    {
                        "content": {
                            "entryType": "TimelineTimelineModule",
                            "items": [
                                {
                                    "item": {
                                        "itemContent": {
                                            "tweet_results": {"result": SAMPLE_TWEET_RESULT}
                                        }
                                    }
                                }
                            ],
                        }
                    }
                ],
            }
        ]
        tweets = parse_timeline_instructions(instructions)
        assert len(tweets) == 1


# ── extract_cursor ───────────────────────────────────────────────────────

class TestExtractCursor:
    def test_bottom_cursor(self):
        cursor = extract_cursor(SAMPLE_TIMELINE_INSTRUCTIONS)
        assert cursor == "cursor_abc123"

    def test_no_cursor(self):
        instructions = [
            {
                "type": "TimelineAddEntries",
                "entries": [
                    {
                        "content": {
                            "entryType": "TimelineTimelineItem",
                            "itemContent": {
                                "tweet_results": {"result": SAMPLE_TWEET_RESULT}
                            },
                        }
                    }
                ],
            }
        ]
        assert extract_cursor(instructions) is None

    def test_empty(self):
        assert extract_cursor([]) is None


# ── TwitterClient ────────────────────────────────────────────────────────

class TestTwitterClient:
    def test_fallback_query_ids(self):
        auth = TwitterAuth(auth_token="test", ct0="test")
        client = TwitterClient(auth)
        # Should use fallback when no cache or discovery
        qid = client.get_query_id("Bookmarks")
        assert qid == FALLBACK_QUERY_IDS["Bookmarks"]
        client.close()

    def test_headers(self):
        auth = TwitterAuth(auth_token="mytoken", ct0="myct0")
        client = TwitterClient(auth)
        headers = client._build_headers()
        assert "Bearer" in headers["Authorization"]
        assert "auth_token=mytoken" in headers["Cookie"]
        assert headers["x-csrf-token"] == "myct0"
        client.close()
