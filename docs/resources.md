# Resources

## Reference Implementation

- **Smaug** — `~/Desktop/lab/projects/reference/smaug/` — the JS codebase we're replacing
  - `upstream/src/processor.js` — fetch, expand, enrich logic (~650 lines)
  - `upstream/src/cli.js` — CLI with setup wizard
  - `upstream/src/config.js` — config management
  - `smaug.config.json` — our active config (has folder IDs, cookie values)

- **Bird CLI** — `@steipete/bird` — X API client that smaug calls
  - Uses X's internal GraphQL API (same endpoints as the web app)
  - Bookmark fetch: `bird bookmarks --folder-id {id} -n 50 --json`
  - Auth: session cookies (auth_token, ct0) passed as env vars
  - Source: https://github.com/nicklama/bird-cli (fork by steipete)

## X API

- **GraphQL endpoint**: `https://x.com/i/api/graphql/`
  - Bookmarks query uses `Bookmarks` feature with pagination cursors
  - Auth: `auth_token` cookie + `ct0` CSRF token + bearer token
  - Bearer token is hardcoded in the web app JS (public, same for all users)
  - Rate limits: ~300 requests per 15 minutes (approximate, undocumented)

## Existing System

- **Automation scripts**: `~/Desktop/lab/automations/bookmark-sync/`
  - `run.sh` — 4-phase pipeline (fetch → triage → deep dive → feedback)
  - `TRIAGE_PROMPT.md`, `DEEPDIVE_PROMPT.md` — Claude headless prompts
  - `com.kenneth.bookmark-sync.plist` — launchd config (5pm daily)

- **Vault data**: `~/Desktop/lab/notes/shoshin-codex/bookmarks/`
  - `bookmark-review-guidance.md` — research interest categories and tier heuristics
  - `reports/` — 70+ deep dive reports
  - `triage/` — triage reports and approval files
  - `engagement-log.md` — which reports have been read

## MCP Servers

- **arxiv-mcp-server** — `uv tool run arxiv-mcp-server`
  - Tools: `search_papers`, `download_paper`, `read_paper`
  - Storage: `~/.arxiv-mcp-server/papers/`
  - Configured in `lab/.mcp.json`

- **arxiv-latex-mcp** — `uvx arxiv-latex-mcp`
  - Raw LaTeX source access

## Claude Code Plugin Docs

- Skills: https://docs.anthropic.com/en/docs/claude-code/skills
- Plugins: https://docs.anthropic.com/en/docs/claude-code/plugins
- MCP integration: https://docs.anthropic.com/en/docs/claude-code/mcp
