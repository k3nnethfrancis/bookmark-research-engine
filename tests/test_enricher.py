"""Tests for bre.enricher — link expansion and content fetching."""

from __future__ import annotations

import pytest

from bre.enricher import classify_link, is_paywalled, _extract_github_info


# ── classify_link ────────────────────────────────────────────────────────

class TestClassifyLink:
    def test_github(self):
        assert classify_link("https://github.com/openai/swarm") == "github"

    def test_youtube(self):
        assert classify_link("https://youtube.com/watch?v=abc") == "video"
        assert classify_link("https://youtu.be/abc") == "video"

    def test_tweet(self):
        assert classify_link("https://x.com/user/status/123") == "tweet"
        assert classify_link("https://twitter.com/user/status/123") == "tweet"

    def test_tweet_media(self):
        assert classify_link("https://x.com/user/status/123/photo/1") == "media"
        assert classify_link("https://x.com/user/status/123/video/1") == "media"

    def test_image(self):
        assert classify_link("https://example.com/image.jpg") == "image"
        assert classify_link("https://example.com/image.PNG") == "image"
        assert classify_link("https://example.com/image.webp") == "image"

    def test_article(self):
        assert classify_link("https://blog.example.com/post") == "article"
        assert classify_link("https://arxiv.org/abs/2411.12345") == "article"
        assert classify_link("https://medium.com/@user/post") == "article"


# ── is_paywalled ─────────────────────────────────────────────────────────

class TestIsPaywalled:
    def test_paywalled(self):
        assert is_paywalled("https://www.nytimes.com/article")
        assert is_paywalled("https://wsj.com/article")
        assert is_paywalled("https://www.bloomberg.com/news")

    def test_not_paywalled(self):
        assert not is_paywalled("https://blog.example.com/post")
        assert not is_paywalled("https://arxiv.org/abs/2411.12345")
        assert not is_paywalled("https://github.com/org/repo")


# ── _extract_github_info ────────────────────────────────────────────────

class TestExtractGithubInfo:
    def test_basic(self):
        result = _extract_github_info("https://github.com/openai/swarm")
        assert result == ("openai", "swarm")

    def test_with_git_suffix(self):
        result = _extract_github_info("https://github.com/org/repo.git")
        assert result == ("org", "repo")

    def test_with_path(self):
        result = _extract_github_info("https://github.com/org/repo/tree/main/src")
        assert result == ("org", "repo")

    def test_not_github(self):
        assert _extract_github_info("https://example.com/path") is None
