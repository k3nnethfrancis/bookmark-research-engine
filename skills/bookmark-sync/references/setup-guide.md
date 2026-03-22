# Bookmark Research Engine Setup Guide

One-time setup for the bookmark research pipeline.

## Prerequisites

- **Claude Code** installed at `~/.local/bin/claude`
- **Python 3.11+** with `uv` for package management

## Step 1: Install BRE

```bash
cd ~/Desktop/lab/projects/bookmark-research-engine
uv pip install -e .
```

Verify: `bre --help`

## Step 2: Run Interactive Setup

```bash
bre setup
```

This will:
1. Prompt for your X authentication cookies (`auth_token`, `ct0`)
2. Test authentication by fetching 1 bookmark
3. Write config to `~/.config/bre/config.yaml`

### Getting X Cookies

1. Open X (x.com) in your browser while logged in
2. Open DevTools → Application → Cookies → x.com
3. Copy these two cookie values:
   - `auth_token` — your session token
   - `ct0` — your CSRF token

These cookies rotate periodically. If the pipeline stops fetching, re-extract them and run `bre setup` again.

## Step 3: Verify

```bash
# Fetch a small batch to test
bre fetch -n 5

# Check status
bre status
```

## Step 4: Install LaunchAgent (optional — for daily automation)

Update `automations/bookmark-sync/run.sh` to use `bre fetch` instead of smaug, then:

```bash
# Symlink plist
ln -sf ~/Desktop/lab/automations/bookmark-sync/com.kenneth.bookmark-sync.plist ~/Library/LaunchAgents/

# Load it
launchctl load ~/Library/LaunchAgents/com.kenneth.bookmark-sync.plist
```

This runs the pipeline daily at 5:00 PM.

## Troubleshooting

### "bre: command not found"
Ensure the package is installed: `uv pip install -e ~/Desktop/lab/projects/bookmark-research-engine`

### No new bookmarks fetched
X cookies may have expired. Run `bre setup` to update them.

### Query ID errors (404)
X rotates GraphQL query IDs periodically. Run `bre refresh-ids` to discover current IDs.

### Bookmarks fetched but not processed
Check `sync.log` for errors in the Claude headless invocation. Common issues:
- Missing API key (Claude Code needs `ANTHROPIC_API_KEY` in environment or OAuth session)
- Permission errors on vault files

## Vault Structure

The pipeline creates and manages this structure in `shoshin-codex/bookmarks/`:

```
bookmarks/
  inbox.md                     # raw bookmark log (Phase 1 output)
  bookmark-review-guidance.md  # interest categories — edit this to tune triage
  engagement-log.md            # tracks which reports you've read
  triage-log.md                # last-processed date for triage
  triage/                      # triage reports + approval files
  archive/                     # rotated old inbox entries (>30 days)
  feedback/                    # monthly engagement analytics
  reports/                     # deep research briefs (the main output)
```
