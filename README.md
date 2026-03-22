# bookmark-research-engine

Turn X bookmarks into ranked, analyzed research briefs. Self-contained Claude Code plugin — no external CLI dependencies.

## Status

- [ ] Phase 1: Core fetch engine (Python rewrite of smaug)
- [ ] Phase 2: Plugin packaging (skill + MCP + install flow)
- [ ] Phase 3: Migration (replace smaug in daily automation)

## Quick Start

```bash
# Install
uv pip install -e .

# Setup (interactive — gets your X cookies, tests auth)
bre setup

# Fetch latest bookmarks
bre fetch

# Check status
bre status
```

Then in Claude Code:
```
> check bookmarks     # status
> triage bookmarks    # rank pending items
> deep dive           # spawn research agents for tier-1 items
```

## What It Does

1. **Fetches** bookmarks from X using session cookies
2. **Enriches** them — expands t.co links, fetches articles, GitHub READMEs, quote tweets
3. **Triages** against your research interests (interactive or automated)
4. **Deep dives** — spawns parallel agents that investigate tier-1 items using WebSearch, WebFetch, and arxiv MCP
5. **Produces** structured research briefs with frontmatter, findings, methodology, implications, and actionable takeaways

## Docs

- `docs/plan.md` — implementation plan and decisions
- `docs/resources.md` — reference links and related systems
