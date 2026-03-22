"""High-level orchestration for bookmark fetching and enrichment.

This is the main entry point that ties together twitter.py, enricher.py,
state.py, and config.py into a single fetch_and_prepare() call.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from bre.config import Config
from bre.enricher import enrich_bookmark
from bre.state import get_archived_ids, load_pending, load_state, merge_pending, save_pending, save_state
from bre.twitter import TwitterClient


async def _fetch_and_prepare_async(
    config: Config,
    count: int = 20,
    folder: str | None = None,
    force: bool = False,
    max_pages: int = 10,
) -> dict:
    """Async implementation of fetch_and_prepare."""
    now = datetime.now(timezone.utc)
    print(f"[{now.isoformat()}] Fetching and preparing bookmarks...")

    with TwitterClient(config.auth, config.query_ids_cache) as twitter:
        # ── Fetch tweets ─────────────────────────────────────────────
        tweets: list[dict] = []

        if folder:
            # Fetch from a specific folder
            target_folders = [f for f in config.folders if f.tag == folder or f.id == folder]
            if not target_folders:
                print(f"Unknown folder: {folder}")
                return {"bookmarks": [], "count": 0}
            for fc in target_folders:
                print(f"Fetching from folder '{fc.tag}' ({fc.id})...")
                folder_tweets = twitter.fetch_all_bookmarks(
                    folder_id=fc.id, max_pages=max_pages, count=count
                )
                for t in folder_tweets:
                    t["_folderTag"] = fc.tag
                tweets.extend(folder_tweets)
        elif config.folders:
            # Fetch from all configured folders
            print(f"Fetching from {len(config.folders)} configured folder(s)...")
            seen_ids: set[str] = set()
            for fc in config.folders:
                print(f"\nFolder '{fc.tag}' ({fc.id}):")
                folder_tweets = twitter.fetch_all_bookmarks(
                    folder_id=fc.id, max_pages=max_pages, count=count
                )
                added = 0
                for t in folder_tweets:
                    if t["id"] not in seen_ids:
                        seen_ids.add(t["id"])
                        t["_folderTag"] = fc.tag
                        tweets.append(t)
                        added += 1
                print(f"  Found {len(folder_tweets)} bookmarks, {added} new")
        else:
            # Fetch from default bookmarks
            print(f"Fetching bookmarks (count={count})...")
            if count > 50:
                tweets = twitter.fetch_all_bookmarks(max_pages=max_pages, count=count)
            else:
                tweets, _ = twitter.fetch_bookmarks(count=count)

        if not tweets:
            print("No bookmarks found")
            return {"bookmarks": [], "count": 0}

        # ── Dedup against archive + existing pending ─────────────────
        archived_ids = get_archived_ids(config.archive_file)
        existing_pending = load_pending(config.pending_file)
        pending_ids = {str(b["id"]) for b in existing_pending["bookmarks"]}

        if force:
            to_process = tweets
        else:
            to_process = [
                t for t in tweets
                if str(t["id"]) not in archived_ids and str(t["id"]) not in pending_ids
            ]

        if not to_process:
            print("No new tweets to process")
            return {"bookmarks": [], "count": 0}

        print(f"Preparing {len(to_process)} tweets...")

        # ── Enrich each tweet ────────────────────────────────────────
        prepared: list[dict] = []
        async with httpx.AsyncClient() as http_client:
            for tweet in to_process:
                try:
                    print(f"\nProcessing bookmark {tweet['id']}...")
                    enriched = await enrich_bookmark(
                        http_client, twitter, tweet,
                        timezone=config.timezone,
                    )
                    prepared.append(enriched)
                    link_info = f"{len(enriched['links'])} links"
                    tag_info = f" [{', '.join(enriched['tags'])}]" if enriched["tags"] else ""
                    reply_info = " (reply)" if enriched["isReply"] else ""
                    quote_info = " (quote)" if enriched["isQuote"] else ""
                    print(f"  Prepared: @{enriched['author']} with {link_info}{tag_info}{reply_info}{quote_info}")
                except Exception as e:
                    print(f"  Error processing bookmark {tweet['id']}: {e}")

        # ── Merge into pending ───────────────────────────────────────
        merged = merge_pending(existing_pending["bookmarks"], prepared)
        output = {
            "generatedAt": now.isoformat(),
            "count": len(merged),
            "bookmarks": merged,
        }
        save_pending(config.pending_file, output)
        print(f"\nMerged {len(prepared)} new bookmarks into {config.pending_file} (total: {len(merged)})")

        # ── Update state ─────────────────────────────────────────────
        state = load_state(config.state_file)
        state["last_check"] = now.isoformat()
        save_state(config.state_file, state)

        return {"bookmarks": prepared, "count": len(prepared), "pendingFile": str(config.pending_file)}


def fetch_and_prepare(
    config: Config,
    count: int = 20,
    folder: str | None = None,
    force: bool = False,
    max_pages: int = 10,
) -> dict:
    """Synchronous wrapper for the async fetch pipeline."""
    return asyncio.run(_fetch_and_prepare_async(config, count, folder, force, max_pages))
