# bookmark-research-engine

Turn X bookmarks into ranked, analyzed research briefs. Self-contained Claude Code plugin — no external CLI dependencies.

## Install

### As a Claude Code plugin (recommended)

Add the marketplace, then install:

```bash
claude plugin install k3nnethfrancis/bookmark-research-engine
```

The plugin auto-installs the `bre` CLI on first session. Then run setup:

```bash
bre setup
```

### Standalone

```bash
pip install git+https://github.com/k3nnethfrancis/bookmark-research-engine.git
bre setup
```

## Usage

### CLI

```bash
bre fetch              # pull bookmarks from X into pending queue
bre fetch -n 50        # fetch 50 bookmarks
bre status             # pipeline health and pending count
bre setup              # interactive setup (cookies, vault, config)
bre refresh-ids        # refresh X GraphQL query IDs
bre enrich input.json  # re-run enrichment on raw tweet JSON
```

### In Claude Code

```
> check bookmarks     # status
> triage bookmarks    # rank pending items against your research interests
> deep dive           # spawn parallel research agents for tier-1 items
> review bookmarks    # summarize findings, connect to projects
```

## What It Does

1. **Fetches** bookmarks from X using session cookies (no bird/smaug dependency)
2. **Enriches** them — expands t.co links, fetches articles, GitHub READMEs, resolves quote tweets
3. **Triages** against your research interests (interactive or automated)
4. **Deep dives** — spawns parallel agents that investigate tier-1 items using WebSearch, WebFetch, and arxiv MCP
5. **Produces** structured research briefs with frontmatter, findings, methodology, implications, and actionable takeaways

## How It Works

The `bre` CLI handles the mechanical fetch and enrichment. The Claude Code skill handles the intelligence — triage ranking, deep dive research, report writing.

```
bre fetch → pending.json → skill triage → approval file → skill deep dive → reports/
```

The vault structure (where reports, triage, and inbox files live) is fully configurable. Default: `~/.config/bre/vault/`. Point `vault_root` at an existing Obsidian vault to integrate.

## Requirements

- Python 3.11+
- Claude Code (for the skill — triage, deep dive, review)
- X account with bookmarks (cookies for auth)
