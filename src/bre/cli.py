"""BRE CLI — bookmark research engine command line interface.

Commands:
    bre fetch       — pull bookmarks from X into pending queue
    bre status      — show pipeline health and pending count
    bre setup       — interactive setup (cookies, test fetch, write config)
    bre enrich      — re-run enrichment on raw tweet JSON
    bre refresh-ids — force-refresh X GraphQL query IDs
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from bre.config import load_config

app = typer.Typer(help="Bookmark Research Engine — turn X bookmarks into research briefs")


@app.command()
def fetch(
    count: int = typer.Option(50, "-n", "--count", help="Number of bookmarks to fetch"),
    folder: str | None = typer.Option(None, "--folder", help="Folder tag or ID to fetch from"),
    force: bool = typer.Option(False, "--force", help="Skip dedup, process all fetched tweets"),
    max_pages: int = typer.Option(10, "--max-pages", help="Max pagination pages"),
    config_path: str | None = typer.Option(None, "--config", help="Path to bre.yaml"),
):
    """Pull new bookmarks from X into the pending queue."""
    config = load_config(config_path)

    if not config.auth.auth_token or not config.auth.ct0:
        typer.echo("Error: Missing auth credentials. Run `bre setup` or set BRE_AUTH_TOKEN/BRE_CT0.")
        raise typer.Exit(1)

    from bre.fetcher import fetch_and_prepare

    result = fetch_and_prepare(config, count=count, folder=folder, force=force, max_pages=max_pages)
    typer.echo(f"\nDone. {result['count']} new bookmarks prepared.")


@app.command()
def status(
    config_path: str | None = typer.Option(None, "--config", help="Path to bre.yaml"),
):
    """Show pipeline health and pending count."""
    config = load_config(config_path)

    from bre.state import load_pending, load_state

    state = load_state(config.state_file)
    pending = load_pending(config.pending_file)

    typer.echo("Bookmark Research Engine — Status")
    typer.echo("─" * 40)
    typer.echo(f"Last check:      {state.get('last_check', 'never')}")
    typer.echo(f"Pending:         {pending['count']} bookmarks")
    typer.echo(f"Pending file:    {config.pending_file}")
    typer.echo(f"State file:      {config.state_file}")
    typer.echo(f"Archive file:    {config.archive_file}")

    # Vault status
    typer.echo(f"\nVault: {config.vault_root}")
    inbox = config.vault.inbox
    if inbox.exists():
        lines = inbox.read_text().count("\n")
        typer.echo(f"  Inbox:         {inbox.name} ({lines} lines)")
    reports = config.vault.reports_dir
    if reports.exists():
        count = len(list(reports.glob("*.md")))
        typer.echo(f"  Reports:       {count} files")
    triage_dir = config.vault.triage_dir
    if triage_dir.exists():
        unprocessed = 0
        for f in triage_dir.glob("*-approved.md"):
            if "processed: true" not in f.read_text():
                unprocessed += 1
        if unprocessed:
            typer.echo(f"  Approvals:     {unprocessed} unprocessed")
    triage_log = config.vault.triage_log
    if triage_log.exists():
        for line in triage_log.read_text().splitlines():
            if line.startswith("last_processed:"):
                typer.echo(f"  Last triage:   {line.split(':', 1)[1].strip()}")

    if pending["bookmarks"]:
        typer.echo(f"\nLatest pending:")
        for b in pending["bookmarks"][-5:]:
            author = b.get("author", "unknown")
            text = b.get("text", "")[:80].replace("\n", " ")
            links = len(b.get("links", []))
            typer.echo(f"  @{author}: {text}... ({links} links)")


@app.command()
def setup(
    config_path: str = typer.Option(
        "~/.config/bre/config.yaml", "--config", help="Where to write config"
    ),
):
    """Interactive setup — prompts for X cookies, tests auth, writes config."""
    import yaml

    target = Path(config_path).expanduser()

    typer.echo("Bookmark Research Engine — Setup")
    typer.echo("─" * 40)
    typer.echo("Extract these from browser DevTools → Application → Cookies → x.com\n")

    auth_token = typer.prompt("auth_token")
    ct0 = typer.prompt("ct0")

    typer.echo("\nTesting authentication...")

    from bre.config import TwitterAuth
    from bre.twitter import TwitterClient

    auth = TwitterAuth(auth_token=auth_token, ct0=ct0)
    try:
        with TwitterClient(auth) as client:
            tweets, _ = client.fetch_bookmarks(count=1)
            if tweets:
                typer.echo(f"  Auth works! Fetched bookmark from @{tweets[0].get('author', {}).get('username', 'unknown')}")
            else:
                typer.echo("  Auth works but no bookmarks found (empty bookmarks list)")
    except Exception as e:
        typer.echo(f"  Auth failed: {e}")
        typer.echo("Check your cookies and try again.")
        raise typer.Exit(1)

    # Ask about vault location
    typer.echo("\nVault setup — where should reports, triage, and inbox files go?")
    vault_root_str = typer.prompt(
        "Vault root",
        default="~/.config/bre/vault",
    )
    vault_root = Path(vault_root_str).expanduser()

    # Write config
    config_data = {
        "auth": {"auth_token": auth_token, "ct0": ct0},
        "folders": {},
        "pending_file": "~/.config/bre/state/pending-bookmarks.json",
        "state_file": "~/.config/bre/state/bookmarks-state.json",
        "timezone": "America/New_York",
        "vault_root": vault_root_str,
        "archive_file": str(Path(vault_root_str) / "bookmarks/inbox.md"),
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.dump(config_data, default_flow_style=False, sort_keys=False))
    typer.echo(f"\nConfig written to {target}")

    # Scaffold vault structure
    typer.echo(f"\nScaffolding vault at {vault_root}...")
    _scaffold_vault(vault_root)

    typer.echo("\nRun `bre fetch` to pull your latest bookmarks.")


# ── Vault Scaffolding ────────────────────────────────────────────────────

INBOX_TEMPLATE = """\
# Bookmark Inbox

Review queue — bookmarks are appended here by the pipeline, newest at bottom.

---

"""

GUIDANCE_TEMPLATE = """\
# Bookmark Review Guidance

What you care about reviewing. This controls how bookmarks are ranked during triage.
Edit this to match your actual research interests.

---

## Your Research Question

> Describe your core research focus here.

---

## Interest Categories

Define 3-7 categories. For each:
- **Trigger signals**: keywords that identify this category
- **Tier 1 vs Tier 2**: what makes something high-priority

### 1. Example Category

Description of what draws you to this topic.

**Trigger signals:** keyword1, keyword2, keyword3

**What makes it Tier 1 vs Tier 2:** Empirical results > theoretical. Surprising > confirmatory.

---

## Ranking Heuristics

### Automatic Tier 1
- Items matching your core research question with empirical results

### Automatic Tier 2
- Incremental improvements, theoretical frameworks without validation

### Automatic Tier 3 (skip)
- Product launches, tutorial content, opinion without data

### Cross-Category Bonus
Items spanning multiple categories rank higher.
"""

ENGAGEMENT_LOG_TEMPLATE = """\
# Engagement Log

Tracks when bookmark reports are read or referenced during sessions.

Format: `- **{action}**: \\`reports/{filename}.md\\` — {context}`

Actions: `read` (opened/discussed), `referenced` (used in research/writing)

---
"""

TRIAGE_LOG_TEMPLATE = """\
# Triage Log

Tracks the last inbox date processed by triage, so subsequent runs know where to start.

---

last_processed: never
"""


def _scaffold_vault(vault_root: Path):
    """Create vault directory structure and seed files if they don't exist."""
    dirs = [
        "bookmarks",
        "bookmarks/reports",
        "bookmarks/triage",
        "bookmarks/archive",
        "bookmarks/feedback",
    ]
    files = {
        "bookmarks/inbox.md": INBOX_TEMPLATE,
        "bookmarks/bookmark-review-guidance.md": GUIDANCE_TEMPLATE,
        "bookmarks/engagement-log.md": ENGAGEMENT_LOG_TEMPLATE,
        "bookmarks/triage-log.md": TRIAGE_LOG_TEMPLATE,
    }

    for d in dirs:
        p = vault_root / d
        if not p.exists():
            p.mkdir(parents=True, exist_ok=True)
            typer.echo(f"  Created {d}/")

    for path, content in files.items():
        p = vault_root / path
        if not p.exists():
            p.write_text(content)
            typer.echo(f"  Created {path}")

    typer.echo(f"\n  Edit bookmarks/bookmark-review-guidance.md to define your research interests.")
    typer.echo(f"  This controls how triage ranks your bookmarks.")


@app.command()
def enrich(
    input_file: str = typer.Argument(..., help="Path to raw tweet JSON"),
    output_file: str | None = typer.Option(None, "-o", "--output", help="Output path (default: stdout)"),
    config_path: str | None = typer.Option(None, "--config", help="Path to bre.yaml"),
):
    """Re-run enrichment on raw tweet JSON."""
    import asyncio

    import httpx

    from bre.enricher import enrich_bookmark
    from bre.twitter import TwitterClient

    config = load_config(config_path)
    tweets = json.loads(Path(input_file).read_text())
    if isinstance(tweets, dict):
        tweets = tweets.get("tweets", tweets.get("bookmarks", [tweets]))

    async def _enrich():
        with TwitterClient(config.auth, config.query_ids_cache) as twitter:
            async with httpx.AsyncClient() as http_client:
                results = []
                for tweet in tweets:
                    enriched = await enrich_bookmark(http_client, twitter, tweet)
                    results.append(enriched)
                return results

    results = asyncio.run(_enrich())
    output = json.dumps({"bookmarks": results, "count": len(results)}, indent=2)

    if output_file:
        Path(output_file).write_text(output)
        typer.echo(f"Enriched {len(results)} tweets → {output_file}")
    else:
        typer.echo(output)


@app.command(name="refresh-ids")
def refresh_ids(
    config_path: str | None = typer.Option(None, "--config", help="Path to bre.yaml"),
):
    """Force-refresh X GraphQL query IDs from JS bundles."""
    config = load_config(config_path)

    from bre.twitter import TwitterClient

    # Only need a client to refresh — no auth required for JS bundle fetching
    auth = config.auth
    with TwitterClient(auth, config.query_ids_cache) as client:
        typer.echo("Discovering query IDs from x.com JS bundles...")
        client.refresh_query_ids()
        typer.echo(f"Cached {len(client._query_ids)} query IDs to {config.query_ids_cache}")
        for op, qid in sorted(client._query_ids.items()):
            typer.echo(f"  {op}: {qid}")


def main():
    app()
