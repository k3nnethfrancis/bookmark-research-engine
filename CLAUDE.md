# Bookmark Research Engine

Self-contained plugin that turns X bookmarks into ranked, analyzed research briefs. Replaces smaug + bird with a single Python package. Distributed via agent-utils as a Claude Code plugin.

## What This Is

A complete research pipeline:
1. **Fetch** — pull bookmarks from X using session cookies (no external CLI dependencies)
2. **Enrich** — expand t.co links, fetch article content, GitHub READMEs, resolve quote tweets
3. **Triage** — rank against user's research interests (interactive or automated)
4. **Deep Dive** — spawn parallel research agents that investigate tier-1 items and write structured reports
5. **Review** — summarize findings, connect to active projects

The plugin packages everything: the Python fetch/enrich engine, the Claude Code skill, and the arxiv MCP config.

## Stack

- **Python 3.11+** with `uv` for package management
- **httpx** — async HTTP for X API, link expansion, content fetching
- **typer** — CLI
- **pyyaml** — config

No external CLI dependencies. The X API interaction uses the same GraphQL endpoint that bird uses, reimplemented in Python.

## Key Files

```
src/bre/
├── __init__.py
├── cli.py              # CLI: bre fetch, bre status, bre enrich
├── fetcher.py          # X bookmark fetching via GraphQL
├── enricher.py         # Link expansion, content extraction, GitHub API
├── config.py           # Config loading and validation
└── state.py            # Dedup state management
```

```
skills/bookmark-sync/
├── SKILL.md            # The Claude Code skill (triage, deep dive, review)
├── scripts/
│   ├── status.sh       # Pipeline health check
│   └── list-pending.sh # Parse and display pending items
├── references/
│   ├── deepdive-agent-prompt.md
│   ├── report-format.md
│   ├── pending-json-schema.md
│   └── setup-guide.md
└── examples/
    └── approval-file.md
```

## Related Paths

- Vault planning: `~/Desktop/lab/notes/shoshin-codex/projects/bookmark-research-engine/`
- Current working system: `~/Desktop/lab/automations/bookmark-sync/` (run.sh, prompts)
- Smaug reference: `~/Desktop/lab/projects/reference/smaug/` (the JS code we're replacing)
- Agent-utils: `~/Desktop/lab/projects/agent-utils/` (distribution target — symlink plugin here)
- Active reports: `~/Desktop/lab/notes/shoshin-codex/bookmarks/reports/` (70+ existing reports)

## Plugin Structure

```
.claude-plugin/
├── plugin.json         # Plugin manifest
└── .mcp.json           # arxiv MCP server config (optional enhancement)
```

When installed via `claude plugin add`, this registers:
- The bookmark-sync skill
- The arxiv MCP server (if user installs arxiv-mcp-server)

## Constraints

- **Don't break existing pipeline.** The current automation (`automations/bookmark-sync/run.sh`) stays functional throughout development. We migrate to the new engine once it's tested.
- **Same output format.** Reports go to `bookmarks/reports/` in the same frontmatter + sections format. Existing 70+ reports must remain compatible.
- **Same pending JSON schema.** The pending-bookmarks.json format stays the same so the skill's triage/deep-dive modes work unchanged.

## Progress Ledger

Read `~/Desktop/lab/notes/shoshin-codex/projects/bookmark-research-engine/progress-ledger.md` at session start.

-- Shoshin | 2026-03-21
