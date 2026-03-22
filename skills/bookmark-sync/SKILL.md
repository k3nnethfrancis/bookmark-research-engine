---
name: bookmark-sync
description: Use when Kenneth mentions bookmarks, research queue, bookmark reports, triage, deep dives, or the bookmark pipeline. Trigger phrases include "bookmark sync", "check bookmarks", "review bookmarks", "triage bookmarks", "deep dive", "run bookmark pipeline", "what's pending", "latest reports", "set up bookmarks". Also triggers on references to specific bookmark report files or the bookmarks/ directory.
---

# Bookmark Sync

Research pipeline that turns X bookmarks into ranked, analyzed research briefs. Supports both automated (daily launchd) and interactive (in-session) workflows.

Powered by the Bookmark Research Engine (`bre` CLI) — a self-contained Python package that fetches and enriches bookmarks without external CLI dependencies.

## Modes

### Status
Check pipeline health and pending work. **Use this first** when Kenneth mentions bookmarks.

Run the status script:
```bash
bash {SKILL_DIR}/scripts/status.sh
```

Then report: last sync date, any errors, pending count, latest triage/report dates.

### Fetch
Pull new bookmarks from X into the pending queue. Runs automatically at 5pm daily, but can be triggered manually.

```bash
bre fetch -n 50
```

Or with a specific folder:
```bash
bre fetch -n 50 --folder research
```

Then check what came in and summarize — authors, topics, link count.

### Triage
Rank pending bookmarks against Kenneth's research interests. Two sub-modes:

**Interactive triage** (preferred when Kenneth is present):
1. List all pending bookmarks:
   ```bash
   bash {SKILL_DIR}/scripts/list-pending.sh
   ```
2. Rank them by relevance to the research arc (Helm, Sigmund, multi-agent control, RL training, research automation, behavioral measurement, novel architectures, agent tooling)
3. Present ranked list in tiers: Tier 1 (deep dive), Tier 2 (skim), Tier 3 (skip)
4. Get Kenneth's confirmation or adjustments
5. Write approval file to `shoshin-codex/bookmarks/triage/YYYY-MM-DD-approved.md`

**Automated triage** (for unattended runs):
Follow the full triage prompt at `automations/bookmark-sync/TRIAGE_PROMPT.md`. Read the guidance doc at `shoshin-codex/bookmarks/bookmark-review-guidance.md` for category definitions and tier heuristics.

**Ranking heuristics** (from guidance doc):
- 7 categories: multi-agent-orchestration, rl-training-methods, ai-safety-alignment-monitoring, behavioral-measurement-llm-psychology, ai-research-automation, novel-architectures-paradigms, agent-tooling-developer-experience
- Cross-category items get bumped up one tier
- Empirical results > theoretical frameworks
- Novel learning loops > hyperparameter tuning
- Surprising findings > confirmatory results

### Deep Dive
Spawn parallel research agents for approved bookmarks. This is the core value — turning bookmarks into analyzed research briefs.

1. Read the approval file from `shoshin-codex/bookmarks/triage/`
2. Read research guidance from `shoshin-codex/bookmarks/bookmark-review-guidance.md`
3. Check existing reports in `shoshin-codex/bookmarks/reports/` — skip duplicates
4. For each approved item, spawn a background Agent with:
   - The bookmark source material (tweet text, expanded URLs, fetched content from pending JSON)
   - Matched research categories and context from the guidance doc
   - Instructions to investigate — **prefer arxiv MCP tools for papers** (see below)
   - Report destination: `shoshin-codex/bookmarks/reports/{slug}.md`

**Agent prompt template** — see `references/deepdive-agent-prompt.md` for the full template. Key: include pre-fetched content from the pending JSON to save agents a fetch, and paste only the matched category descriptions from the guidance doc (not all 7).

**arxiv MCP tools** — available as `mcp__arxiv__search_papers`, `mcp__arxiv__download_paper`, `mcp__arxiv__read_paper`:
- When a bookmark links to an arxiv paper, agents should use `download_paper` (by arxiv ID) then `read_paper` to get the full markdown content — much better than WebFetch on arxiv HTML
- When a bookmark mentions a paper without a direct link, use `search_papers` with query + category filters to find it
- Papers are cached at `~/.arxiv-mcp-server/papers/` — subsequent reads are instant
- Also available: `mcp__arxiv-latex__` tools for raw LaTeX source when needed

**Report format** — see `references/report-format.md` for the full template.

**Parallelism**: Up to 7 agents concurrently. Use `run_in_background=true` on all Agent calls.

5. As agents complete, summarize findings to Kenneth
6. Mark approval file as processed (append `processed: true`)

### Review
Discuss completed reports and connect findings to active projects.

1. Read recent reports from `shoshin-codex/bookmarks/reports/`
2. Summarize key findings, cross-cutting themes, and project implications
3. If Kenneth wants a research queue note for a project, write one to the relevant project's vault directory or repo docs

### Setup
Guide through initial setup of the bookmark research engine.

```bash
bre setup
```

This interactively prompts for X cookies, tests authentication, and writes the config file. See `references/setup-guide.md` for the full walkthrough.

## Paths

All vault paths are configurable in `bre.yaml` under `vault_root` + `vault.*`. Defaults shown.

| What | Where | Config key |
|------|-------|-----------|
| BRE CLI | `bre` (installed via `uv pip install -e .`) | — |
| BRE config | `~/.config/bre/config.yaml` | — |
| Pipeline scripts | `automations/bookmark-sync/` | — |
| Pending bookmarks | `projects/reference/smaug/.state/pending-bookmarks.json` | `pending_file` |
| Vault root | `shoshin-codex/` | `vault_root` |
| Inbox | `shoshin-codex/bookmarks/inbox.md` | `vault.inbox` |
| Research guidance | `shoshin-codex/bookmarks/bookmark-review-guidance.md` | `vault.guidance` |
| Triage reports | `shoshin-codex/bookmarks/triage/` | `vault.triage_dir` |
| Triage log | `shoshin-codex/bookmarks/triage-log.md` | `vault.triage_log` |
| Deep dive reports | `shoshin-codex/bookmarks/reports/` | `vault.reports_dir` |
| Engagement log | `shoshin-codex/bookmarks/engagement-log.md` | `vault.engagement_log` |
| Feedback reports | `shoshin-codex/bookmarks/feedback/` | `vault.feedback_dir` |
| Sync log | `automations/bookmark-sync/sync.log` |

## Rules

- **Never write to `garden/`** unless Kenneth explicitly says to
- Always use `date` command for timestamps — never guess
- Update engagement log when reading reports: `- **read**: \`reports/{filename}.md\` — {context}`
- Mark approval files as processed after deep dive completes
- Reports use slugified filenames: lowercase, hyphens, no special characters

## Gotchas

- **X cookie expiry**: `auth_token` and `ct0` rotate periodically. If fetch returns 0 new bookmarks unexpectedly, re-extract cookies from browser DevTools. Run `bre setup` to update them.
- **Query ID rotation**: X rotates GraphQL query IDs. If `bre fetch` returns 404 errors, run `bre refresh-ids` to discover current IDs from X's JS bundles.
- **Pending JSON path**: The state file is at `projects/reference/smaug/.state/pending-bookmarks.json`. The `reference/` prefix matters.
- **WebFetch failures in agents**: Some sources (especially X/Twitter) block scraping. Agents should fall back to WebSearch when WebFetch fails. The pre-fetched content from the pending JSON is often sufficient — always include it in the agent prompt to avoid redundant fetches.
- **Deep dive agent count**: 7 concurrent agents works fine. Don't go much higher — diminishing returns and rate limit risk.
- **Approval file format**: Must end with `processed: true` on its own line to be skipped by subsequent runs. Append it, don't rewrite the file.
- **Triage log staleness**: If `triage-log.md` has an old `last_processed` date, triage will try to process a large backlog. Check it before running triage on accumulated bookmarks.
- **arxiv MCP availability**: The arxiv MCP servers (`arxiv`, `arxiv-latex`) are configured in the plugin's `.mcp.json` but may not be connected in every session. If `mcp__arxiv__` tools aren't available, fall back to WebFetch on arxiv abstract pages. The MCP gives full paper text; WebFetch only gets the abstract page HTML.

## File Structure

```
bookmark-sync/
├── SKILL.md                           # This file
├── scripts/
│   ├── status.sh                      # Quick pipeline health check
│   └── list-pending.sh                # Parse and display pending items
├── references/
│   ├── report-format.md               # Deep dive report template
│   ├── deepdive-agent-prompt.md       # Agent prompt template
│   ├── pending-json-schema.md         # Pending JSON structure
│   └── setup-guide.md                 # First-time setup walkthrough
└── examples/
    └── approval-file.md               # Example triage approval
```
