"""X (Twitter) GraphQL client for bookmark fetching.

Replaces the bird CLI entirely. Uses the same GraphQL endpoints that the X web
client uses, authenticated via session cookies.

Query ID management follows bird's 3-layer approach:
1. Hardcoded fallback IDs (work until X rotates them)
2. Dynamic discovery from X's JS bundles (cached with TTL)
3. On-404 retry: refresh IDs and retry once
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import httpx

from bre.config import Config, TwitterAuth

# Hardcoded fallback query IDs — extracted from bird v0.8.0
# These rotate periodically; dynamic discovery refreshes them.
FALLBACK_QUERY_IDS: dict[str, str] = {
    # Legacy operations (may be retired — server returns 422)
    "Bookmarks": "RV1g3b8n_SGOHwkqKYSCFw",
    "BookmarkFolderTimeline": "KJIQpsvxrTfRIlbaRIySHQ",
    # Current operations (as of 2026-03)
    "BookmarkSearchTimeline": "MAJ05S9KeZYGt-TSPQJCuQ",
    "TweetDetail": "xIYgDwjboktoFeXe_fgacw",
}

# Query ID cache TTL: 1 hour
QUERY_ID_TTL = 3600

# Feature flags sent with bookmark GraphQL requests
BOOKMARK_FEATURES = {
    "graphql_timeline_v2_bookmark_timeline": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
    "responsive_web_media_download_video_enabled": False,
    "rweb_tipjar_consumption_enabled": True,
    "articles_preview_enabled": True,
    "communities_web_enable_tweet_community_results_fetch": True,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
}

TWEET_DETAIL_FEATURES = {
    **BOOKMARK_FEATURES,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
}

# Browser-like headers to avoid detection
BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "x-twitter-active-user": "yes",
    "x-twitter-client-language": "en",
    "x-twitter-auth-type": "OAuth2Session",
}

# Required variables for bookmark requests (added by X, causes 422 if missing)
_BOOKMARK_VARIABLES = {
    "withDownvotePerspective": False,
    "withReactionsMetadata": False,
    "withReactionsPerspective": False,
}

GRAPHQL_BASE = "https://x.com/i/api/graphql"


class TwitterClient:
    """Client for X's GraphQL API using session cookie authentication."""

    def __init__(self, auth: TwitterAuth, query_ids_cache: Path | None = None):
        self.auth = auth
        self.query_ids_cache = query_ids_cache or Path("~/.config/bre/query-ids.json").expanduser()
        self._query_ids: dict[str, str] = {}
        self._query_ids_loaded_at: float = 0
        self.client = httpx.Client(
            headers=self._build_headers(),
            timeout=30.0,
            follow_redirects=True,
        )

    def _build_headers(self) -> dict[str, str]:
        return {
            **BASE_HEADERS,
            "Authorization": f"Bearer {self.auth.bearer_token}",
            "Cookie": f"auth_token={self.auth.auth_token}; ct0={self.auth.ct0}",
            "x-csrf-token": self.auth.ct0,
        }

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    # ── Query ID Management ──────────────────────────────────────────────

    def get_query_id(self, operation: str) -> str:
        """Get query ID for an operation, using cache/discovery/fallback."""
        # Check in-memory cache (with TTL)
        if self._query_ids and (time.time() - self._query_ids_loaded_at < QUERY_ID_TTL):
            if operation in self._query_ids:
                return self._query_ids[operation]

        # Try loading from disk cache
        if self._load_cached_query_ids():
            if operation in self._query_ids:
                return self._query_ids[operation]

        # Try dynamic discovery
        try:
            self._discover_query_ids()
            if operation in self._query_ids:
                return self._query_ids[operation]
        except Exception:
            pass

        # Fallback to hardcoded
        if operation in FALLBACK_QUERY_IDS:
            return FALLBACK_QUERY_IDS[operation]

        raise ValueError(f"No query ID found for operation: {operation}")

    def _load_cached_query_ids(self) -> bool:
        """Load query IDs from disk cache if fresh enough."""
        try:
            if not self.query_ids_cache.exists():
                return False
            data = json.loads(self.query_ids_cache.read_text())
            cached_at = data.get("cached_at", 0)
            if time.time() - cached_at > QUERY_ID_TTL:
                return False
            self._query_ids = data.get("ids", {})
            self._query_ids_loaded_at = cached_at
            return bool(self._query_ids)
        except Exception:
            return False

    def _save_query_ids_cache(self):
        """Persist discovered query IDs to disk."""
        self.query_ids_cache.parent.mkdir(parents=True, exist_ok=True)
        self.query_ids_cache.write_text(json.dumps({
            "cached_at": time.time(),
            "ids": self._query_ids,
        }, indent=2))

    def _discover_query_ids(self):
        """Scrape x.com for JS bundle URLs and extract query IDs.

        X's web client loads JS bundles that contain {queryId, operationName}
        pairs. We fetch the main page, find bundle URLs, then regex-extract.

        Uses a separate unauthenticated client — x.com returns 401 if the
        API bearer token is present on a page request.
        """
        # Use a plain client without auth headers for page/bundle fetching
        with httpx.Client(
            headers={"User-Agent": BASE_HEADERS["User-Agent"]},
            timeout=15.0,
            follow_redirects=True,
        ) as plain:
            resp = plain.get("https://x.com")
            resp.raise_for_status()

            # Find JS bundle URLs
            bundle_urls = re.findall(
                r'src="(https://abs\.twimg\.com/responsive-web/client-web[^"]+\.js)"',
                resp.text,
            )
            if not bundle_urls:
                bundle_urls = re.findall(
                    r'"(https://abs\.twimg\.com/responsive-web/[^"]+\.js)"',
                    resp.text,
                )

            discovered: dict[str, str] = {}
            for url in bundle_urls[:10]:
                try:
                    js_resp = plain.get(url)
                    matches = re.findall(
                        r'\{queryId:"([^"]+)",operationName:"([^"]+)"',
                        js_resp.text,
                    )
                    for query_id, operation in matches:
                        discovered[operation] = query_id
                except Exception:
                    continue

        if discovered:
            self._query_ids = discovered
            self._query_ids_loaded_at = time.time()
            self._save_query_ids_cache()

    def refresh_query_ids(self):
        """Force-refresh query IDs from X's JS bundles."""
        # Clear cache
        if self.query_ids_cache.exists():
            self.query_ids_cache.unlink()
        self._query_ids = {}
        self._query_ids_loaded_at = 0
        self._discover_query_ids()

    # ── GraphQL Requests ─────────────────────────────────────────────────

    def _graphql_get(
        self, operation: str, variables: dict, features: dict | None = None
    ) -> dict[str, Any]:
        """Make a GraphQL GET request to X's API.

        On 404, refreshes query IDs and retries once.
        """
        query_id = self.get_query_id(operation)
        url = f"{GRAPHQL_BASE}/{query_id}/{operation}"
        params = {
            "variables": json.dumps(variables),
            "features": json.dumps(features or BOOKMARK_FEATURES),
        }

        resp = self.client.get(url, params=params)

        # On 404 or 422 (stale query ID or changed features), refresh and retry once
        if resp.status_code in (404, 422):
            self.refresh_query_ids()
            query_id = self.get_query_id(operation)
            url = f"{GRAPHQL_BASE}/{query_id}/{operation}"
            resp = self.client.get(url, params=params)

        if not resp.is_success:
            # Log response body for debugging before raising
            try:
                body = resp.json()
                errors = body.get("errors", [])
                if errors:
                    msgs = "; ".join(e.get("message", str(e)) for e in errors)
                    raise httpx.HTTPStatusError(
                        f"{resp.status_code} {operation}: {msgs}",
                        request=resp.request,
                        response=resp,
                    )
            except (json.JSONDecodeError, ValueError):
                pass
            resp.raise_for_status()

        return resp.json()

    # ── Bookmark Fetching ────────────────────────────────────────────────

    def fetch_bookmarks(self, count: int = 20, cursor: str | None = None) -> tuple[list[dict], str | None]:
        """Fetch a page of bookmarks.

        Returns (tweets, next_cursor). next_cursor is None when no more pages.
        """
        variables: dict[str, Any] = {
            "count": count,
            **_BOOKMARK_VARIABLES,
        }
        if cursor:
            variables["cursor"] = cursor

        data = self._graphql_get("Bookmarks", variables)
        instructions = _extract_instructions(data, "bookmark_timeline_v2")
        tweets = parse_timeline_instructions(instructions)
        next_cursor = extract_cursor(instructions)
        return tweets, next_cursor

    def fetch_bookmark_folder(
        self, folder_id: str, count: int = 20, cursor: str | None = None
    ) -> tuple[list[dict], str | None]:
        """Fetch a page of bookmarks from a specific folder."""
        variables: dict[str, Any] = {
            "bookmark_collection_id": folder_id,
            "count": count,
            **_BOOKMARK_VARIABLES,
        }
        if cursor:
            variables["cursor"] = cursor

        data = self._graphql_get("BookmarkFolderTimeline", variables)
        # Folder endpoint uses a different data key
        instructions = _extract_instructions(data, "bookmark_collection_timeline")
        if not instructions:
            # Fall back to the other key name
            instructions = _extract_instructions(data, "bookmark_timeline_v2")
        tweets = parse_timeline_instructions(instructions)
        next_cursor = extract_cursor(instructions)
        return tweets, next_cursor

    def fetch_tweet(self, tweet_id: str) -> dict | None:
        """Fetch a single tweet by ID (for reply/quote context)."""
        variables = {
            "focalTweetId": tweet_id,
            "with_rux_injections": False,
            "rankingMode": "Relevance",
            "includePromotedContent": True,
            "withCommunity": True,
            "withQuickPromoteEligibilityTweetFields": True,
            "withBirdwatchNotes": True,
            "withVoice": True,
        }
        try:
            data = self._graphql_get("TweetDetail", variables, features=TWEET_DETAIL_FEATURES)
            instructions = _extract_instructions(data, "threaded_conversation_with_injections_v2")
            # TweetDetail returns the focal tweet in the first entry
            for instruction in instructions:
                if instruction.get("type") == "TimelineAddEntries":
                    for entry in instruction.get("entries", []):
                        content = entry.get("content", {})
                        if content.get("entryType") == "TimelineTimelineItem":
                            result = (
                                content
                                .get("itemContent", {})
                                .get("tweet_results", {})
                                .get("result", {})
                            )
                            parsed = parse_tweet_result(result)
                            if parsed and parsed.get("id") == tweet_id:
                                return parsed
            return None
        except Exception:
            return None

    def fetch_all_bookmarks(
        self,
        folder_id: str | None = None,
        max_pages: int = 10,
        count: int = 20,
        delay: float = 1.0,
    ) -> list[dict]:
        """Paginate through all bookmarks, returning the full list."""
        all_tweets: list[dict] = []
        cursor: str | None = None

        for page in range(max_pages):
            if folder_id:
                tweets, cursor = self.fetch_bookmark_folder(folder_id, count, cursor)
            else:
                tweets, cursor = self.fetch_bookmarks(count, cursor)

            all_tweets.extend(tweets)

            if not cursor or not tweets:
                break

            if page < max_pages - 1 and delay > 0:
                time.sleep(delay)

        return all_tweets


# ── Response Parsing ─────────────────────────────────────────────────────

def _extract_instructions(data: dict, timeline_key: str) -> list[dict]:
    """Navigate X's nested response to get timeline instructions."""
    try:
        timeline = data["data"][timeline_key]["timeline"]
        return timeline.get("instructions", [])
    except (KeyError, TypeError):
        return []


def parse_timeline_instructions(instructions: list[dict]) -> list[dict]:
    """Extract tweet dicts from X's timeline instruction format."""
    tweets: list[dict] = []

    for instruction in instructions:
        if instruction.get("type") == "TimelineAddEntries":
            for entry in instruction.get("entries", []):
                content = entry.get("content", {})

                # Regular timeline items
                if content.get("entryType") == "TimelineTimelineItem":
                    result = (
                        content
                        .get("itemContent", {})
                        .get("tweet_results", {})
                        .get("result", {})
                    )
                    parsed = parse_tweet_result(result)
                    if parsed:
                        tweets.append(parsed)

                # Module items (used in some timeline views)
                elif content.get("entryType") == "TimelineTimelineModule":
                    for item in content.get("items", []):
                        item_content = item.get("item", {}).get("itemContent", {})
                        result = item_content.get("tweet_results", {}).get("result", {})
                        parsed = parse_tweet_result(result)
                        if parsed:
                            tweets.append(parsed)

    return tweets


def parse_tweet_result(result: dict) -> dict | None:
    """Normalize a tweet result from X's GraphQL response into a flat dict.

    Handles both regular tweets and tombstoned/withheld tweets.
    The output format matches what smaug/bird produce so downstream code
    (enricher, skill) works unchanged.
    """
    if not result:
        return None

    # Handle tweet-with-visibility wrapper
    if result.get("__typename") == "TweetWithVisibilityResults":
        result = result.get("tweet", {})

    # Skip tombstoned tweets
    if result.get("__typename") == "TweetTombstone":
        return None

    core = result.get("core", {}).get("user_results", {}).get("result", {})
    legacy = result.get("legacy", {})
    user_legacy = core.get("legacy", {})
    # X moved screen_name/name from legacy to core in some responses (2026-03)
    user_core = core.get("core", {})

    tweet_id = result.get("rest_id") or legacy.get("id_str")
    if not tweet_id:
        return None

    text = legacy.get("full_text", "")
    created_at = legacy.get("created_at", "")

    # Author info — check both user_core (new) and user_legacy (old)
    author_username = (
        user_core.get("screen_name")
        or user_legacy.get("screen_name")
        or "unknown"
    )
    author_name = (
        user_core.get("name")
        or user_legacy.get("name")
        or author_username
    )

    # Reply info
    in_reply_to = legacy.get("in_reply_to_status_id_str")

    # Quote tweet (embedded)
    quoted_tweet = None
    qt_results = result.get("quoted_status_result", {}).get("result")
    if qt_results:
        quoted_tweet = parse_tweet_result(qt_results)

    # Media
    media = []
    for m in legacy.get("extended_entities", {}).get("media", []):
        media.append({
            "type": m.get("type", "photo"),
            "url": m.get("media_url_https", ""),
            "expanded_url": m.get("expanded_url", ""),
        })

    return {
        "id": tweet_id,
        "text": text,
        "createdAt": created_at,
        "author": {"username": author_username, "name": author_name},
        "inReplyToStatusId": in_reply_to,
        "quotedTweet": quoted_tweet,
        "media": media,
    }


def extract_cursor(instructions: list[dict]) -> str | None:
    """Extract the pagination cursor from timeline instructions.

    X uses a "Bottom" cursor entry to signal more pages.
    """
    for instruction in instructions:
        if instruction.get("type") == "TimelineAddEntries":
            for entry in instruction.get("entries", []):
                content = entry.get("content", {})
                if content.get("cursorType") == "Bottom":
                    return content.get("value")
                # Some responses nest cursor differently
                if content.get("entryType") == "TimelineTimelineCursor":
                    if content.get("cursorType") == "Bottom":
                        return content.get("value")
    return None
