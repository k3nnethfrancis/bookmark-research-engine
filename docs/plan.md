# Plan

## Goal

A single installable plugin that takes X bookmarks and produces ranked, analyzed research briefs. No external CLI dependencies. Works end-to-end out of the box.

## Approach

Rewrite smaug's JS fetch/enrich pipeline in Python. Package with the existing bookmark-sync skill (triage + deep dive + review). Distribute as a Claude Code plugin via agent-utils.

## Phases

### Phase 1: Core Fetch Engine
Rewrite smaug's `processor.js` in Python. This is the critical path — everything else depends on having bookmarks in the pending JSON format.

- [ ] `fetcher.py` — X bookmark fetch via GraphQL (replaces bird CLI)
  - Auth via session cookies (auth_token, ct0)
  - Paginated fetch from bookmark folders
  - Dedup against existing state
- [ ] `enricher.py` — link expansion and content extraction (replaces smaug's expand/fetch logic)
  - t.co link resolution via HEAD requests
  - Article content fetch (with paywall detection)
  - GitHub repo metadata + README via API
  - Quote tweet and reply context resolution
- [ ] `state.py` — state management (pending JSON, processed IDs, last fetch timestamp)
- [ ] `config.py` — config loading (cookies, paths, folder IDs, timezone)
- [ ] `cli.py` — `bre fetch`, `bre status`, `bre enrich`

**Validation:** Run `bre fetch` and compare output JSON against smaug's `pending-bookmarks.json` for the same bookmarks. Schema must match exactly.

### Phase 2: Plugin Packaging
Package the Python engine + skill + MCP config as an installable Claude Code plugin.

- [ ] `plugin.json` manifest
- [ ] `.mcp.json` with arxiv MCP (optional — skill degrades gracefully without it)
- [ ] Skill files migrated from local `.claude/skills/bookmark-sync/` with all improvements (gotchas, scripts, schemas, agent prompt with arxiv MCP instructions)
- [ ] Setup flow: `bre setup` interactive wizard (like smaug's) — gets cookies, tests auth, creates config
- [ ] `pyproject.toml` for installability

**Validation:** `claude plugin add ./` works. Skill triggers on "check bookmarks". Full pipeline runs: fetch → triage → deep dive → reports.

### Phase 3: Migration
Switch Kenneth's daily automation from smaug to the new engine.

- [ ] Update `automations/bookmark-sync/run.sh` to call `bre` instead of smaug
- [ ] Verify launchd automation works with new engine
- [ ] Symlink plugin into agent-utils: `ln -s ~/Desktop/lab/projects/bookmark-research-engine ~/Desktop/lab/projects/agent-utils/plugins/bookmark-sync`
- [ ] Update agent-utils README

**Validation:** Daily 5pm automation produces reports. No regressions in quality or format.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | Python | Rest of ecosystem (Helm, Prime) is Python. Agents write it well. No build step. |
| X API approach | Direct GraphQL (same as bird) | Removes bird as dependency. We own the code. |
| Config format | YAML | Consistent with Helm. Human-readable. |
| Plugin vs Skill | Plugin | Bundles multiple component types (scripts + skill + MCP). Components depend on each other. |
| Pending JSON schema | Same as smaug | Backwards compatible with existing skill, 70+ reports, triage logic. |

## Open Questions

- **X API stability**: Bird's GraphQL approach works but is unofficial. How brittle is it? Do we need fallback strategies?
- **Rate limiting**: How aggressively can we fetch? Bird seems to handle this — we need to match its behavior.
- **arxiv MCP bundling**: Should the plugin install arxiv-mcp-server automatically, or just document it as an optional enhancement?

-- Shoshin | 2026-03-21
