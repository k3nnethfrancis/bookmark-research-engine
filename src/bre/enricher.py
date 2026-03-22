"""Link expansion and content enrichment.

Port of smaug processor.js lines 220-600. Handles:
- t.co link expansion via HTTP HEAD redirect following
- Link classification (github, article, tweet, video, image, media)
- GitHub API content fetching (repo info + README)
- Article content fetching with paywall detection
- Full bookmark enrichment pipeline (expand → classify → fetch → context)
"""

from __future__ import annotations

import re
from base64 import b64decode
from urllib.parse import urlparse

import httpx

from bre.twitter import TwitterClient

PAYWALL_DOMAINS = [
    "nytimes.com",
    "wsj.com",
    "washingtonpost.com",
    "theatlantic.com",
    "newyorker.com",
    "bloomberg.com",
    "ft.com",
    "economist.com",
    "bostonglobe.com",
    "latimes.com",
    "wired.com",
]

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


async def expand_tco_link(client: httpx.AsyncClient, url: str) -> str:
    """Expand a t.co short URL by following redirects via HEAD request."""
    try:
        resp = await client.head(url, follow_redirects=True, timeout=10.0)
        return str(resp.url) or url
    except Exception:
        return url


def classify_link(url: str) -> str:
    """Classify an expanded URL into a content type."""
    if "github.com" in url:
        return "github"
    if "youtube.com" in url or "youtu.be" in url:
        return "video"
    if "x.com" in url or "twitter.com" in url:
        if "/photo/" in url or "/video/" in url:
            return "media"
        return "tweet"
    if re.search(r"\.(jpg|jpeg|png|gif|webp)$", url, re.IGNORECASE):
        return "image"
    return "article"


def is_paywalled(url: str) -> bool:
    return any(domain in url for domain in PAYWALL_DOMAINS)


def _extract_github_info(url: str) -> tuple[str, str] | None:
    match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
    if not match:
        return None
    return match.group(1), match.group(2).removesuffix(".git")


async def fetch_github_content(client: httpx.AsyncClient, url: str) -> dict:
    """Fetch repo info + README from GitHub API."""
    info = _extract_github_info(url)
    if not info:
        raise ValueError(f"Could not parse GitHub URL: {url}")

    owner, repo = info
    api_base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {"Accept": "application/vnd.github.v3+json"}

    repo_resp = await client.get(api_base, headers=headers, timeout=15.0)
    repo_resp.raise_for_status()
    repo_data = repo_resp.json()

    # Fetch README
    readme = ""
    try:
        readme_resp = await client.get(f"{api_base}/readme", headers=headers, timeout=15.0)
        if readme_resp.status_code == 200:
            readme_data = readme_resp.json()
            if readme_data.get("content"):
                readme = b64decode(readme_data["content"]).decode("utf-8", errors="replace")
                if len(readme) > 5000:
                    readme = readme[:5000] + "\n...[truncated]"
    except Exception:
        pass

    return {
        "name": repo_data.get("name"),
        "fullName": repo_data.get("full_name"),
        "description": repo_data.get("description", ""),
        "stars": repo_data.get("stargazers_count"),
        "language": repo_data.get("language"),
        "topics": repo_data.get("topics", []),
        "readme": readme,
        "url": repo_data.get("html_url"),
        "source": "github-api",
    }


async def fetch_article_content(client: httpx.AsyncClient, url: str) -> dict:
    """Fetch article page content, detecting paywalls."""
    resp = await client.get(
        url,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=30.0,
    )
    text = resp.text[:50000]  # Limit to 50KB

    paywalled = (
        ("Subscribe" in text and "sign in" in text)
        or "This article is for subscribers" in text
        or len(text) < 1000
    )

    return {"text": text, "source": "direct", "paywalled": paywalled}


async def fetch_content(client: httpx.AsyncClient, url: str, link_type: str) -> dict | None:
    """Dispatch content fetching by link type."""
    if link_type == "github":
        try:
            return await fetch_github_content(client, url)
        except Exception:
            pass

    if is_paywalled(url):
        return {"url": url, "source": "paywalled", "note": "Content requires paywall bypass"}

    try:
        return await fetch_article_content(client, url)
    except Exception:
        return None


async def enrich_bookmark(
    http_client: httpx.AsyncClient,
    twitter: TwitterClient,
    tweet: dict,
    *,
    include_media: bool = False,
    timezone: str = "America/New_York",
) -> dict:
    """Full enrichment pipeline for a single tweet.

    Matches smaug's output format so the skill's triage/deep-dive works unchanged:
    - Expand t.co links → classify → fetch content
    - Resolve quote tweet and reply context
    - Build the prepared bookmark dict
    """
    text = tweet.get("text", "")
    author = tweet.get("author", {})
    username = author.get("username", "unknown")
    author_name = author.get("name", username)
    tweet_id = tweet["id"]
    created_at = tweet.get("createdAt", "")

    # Format date
    date = ""
    if created_at:
        try:
            from datetime import datetime
            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            date = dt.strftime("%A, %B %-d, %Y")
        except Exception:
            date = created_at

    # ── Expand and classify t.co links ───────────────────────────────
    tco_links = re.findall(r"https?://t\.co/\w+", text)
    links: list[dict] = []

    for link in tco_links:
        expanded = await expand_tco_link(http_client, link)
        link_type = classify_link(expanded)
        content = None

        # Quote tweet via link
        if link_type == "tweet":
            tweet_id_match = re.search(r"status/(\d+)", expanded)
            if tweet_id_match:
                quoted = twitter.fetch_tweet(tweet_id_match.group(1))
                if quoted:
                    qt_author = quoted.get("author", {})
                    content = {
                        "id": quoted["id"],
                        "author": qt_author.get("username", "unknown"),
                        "authorName": qt_author.get("name", "unknown"),
                        "text": quoted.get("text", ""),
                        "tweetUrl": f"https://x.com/{qt_author.get('username', 'unknown')}/status/{quoted['id']}",
                        "source": "quote-tweet",
                    }

        # Fetch content for articles and GitHub repos
        if link_type in ("article", "github"):
            fetched = await fetch_content(http_client, expanded, link_type)
            if fetched:
                if fetched.get("source") == "github-api":
                    content = fetched
                else:
                    content = {
                        "text": (fetched.get("text") or "")[:10000],
                        "source": fetched.get("source"),
                        "paywalled": fetched.get("paywalled"),
                    }

        links.append({
            "original": link,
            "expanded": expanded,
            "type": link_type,
            "content": content,
        })

    # ── Reply context ────────────────────────────────────────────────
    reply_context = None
    in_reply_to = tweet.get("inReplyToStatusId")
    if in_reply_to:
        parent = twitter.fetch_tweet(in_reply_to)
        if parent:
            p_author = parent.get("author", {})
            reply_context = {
                "id": parent["id"],
                "author": p_author.get("username", "unknown"),
                "authorName": p_author.get("name", "unknown"),
                "text": parent.get("text", ""),
                "tweetUrl": f"https://x.com/{p_author.get('username', 'unknown')}/status/{parent['id']}",
            }

    # ── Native quote tweet ───────────────────────────────────────────
    quote_context = None
    qt = tweet.get("quotedTweet")
    if qt:
        qt_author = qt.get("author", {})
        quote_context = {
            "id": qt["id"],
            "author": qt_author.get("username", "unknown"),
            "authorName": qt_author.get("name", "unknown"),
            "text": qt.get("text", ""),
            "tweetUrl": f"https://x.com/{qt_author.get('username', 'unknown')}/status/{qt['id']}",
            "source": "native-quote",
        }

    # ── Media ────────────────────────────────────────────────────────
    media = tweet.get("media", []) if include_media else []

    # ── Tags ─────────────────────────────────────────────────────────
    tags = []
    if tweet.get("_folderTag"):
        tags.append(tweet["_folderTag"])

    return {
        "id": tweet_id,
        "author": username,
        "authorName": author_name,
        "text": text,
        "tweetUrl": f"https://x.com/{username}/status/{tweet_id}",
        "createdAt": created_at,
        "links": links,
        "media": media,
        "tags": tags,
        "date": date,
        "isReply": bool(in_reply_to),
        "replyContext": reply_context,
        "isQuote": bool(quote_context),
        "quoteContext": quote_context,
    }
