# Pending Bookmarks JSON Schema

The pending bookmarks file lives at `projects/reference/smaug/.state/pending-bookmarks.json`.

Produced by `bre fetch`. Consumed by triage and deep dive.

## Structure

```json
{
  "count": 28,
  "bookmarks": [
    {
      "id": "2033926272481718523",
      "author": "UnslothAI",
      "text": "Introducing Unsloth Studio...",
      "tweetUrl": "https://x.com/UnslothAI/status/2033926272481718523",
      "createdAt": "Wed Oct 10 20:19:24 +0000 2018",
      "links": [
        {
          "original": "https://t.co/ENuTWal5AA",
          "expanded": "https://unsloth.ai/docs/new/studio",
          "type": "article",
          "content": {
            "text": "...(fetched page content)...",
            "source": "direct",
            "paywalled": false
          }
        },
        {
          "original": "https://t.co/2kXqhhvLsb",
          "expanded": "https://github.com/unslothai/unsloth",
          "type": "github",
          "content": {
            "name": "unsloth",
            "fullName": "unslothai/unsloth",
            "description": "...",
            "stars": 54625,
            "language": "Python",
            "readme": "...(full README)...",
            "url": "https://github.com/unslothai/unsloth",
            "source": "github-api"
          }
        }
      ]
    }
  ]
}
```

## Key Fields

| Field | Type | Notes |
|-------|------|-------|
| `author` | string | X username without @ |
| `text` | string | Full tweet text |
| `tweetUrl` | string | Reconstructed tweet URL |
| `createdAt` | string | X's date format |
| `links[].original` | string | t.co shortened URL |
| `links[].expanded` | string | Resolved URL — use this |
| `links[].type` | string | `article`, `github`, `media`, `tweet`, `video`, `image` |
| `links[].content` | object or null | Pre-fetched content if available |
| `links[].content.text` | string | Raw page HTML/text (for articles) |
| `links[].content.readme` | string | GitHub README (for repos) |

## Important Notes

- **Pre-fetched content is the biggest time saver.** When spawning deep-dive agents, include the `links[].content` in the agent prompt. This saves the agent from re-fetching the same URLs.
- **`tweetUrl` is always populated.** Constructed from author and id fields.
- **`type: "media"` links have null content.** These are images/videos that can't be fetched as text.
- **GitHub content includes full README.** This is often sufficient for repo-based bookmarks without additional fetching.
- **arxiv links** can be identified by checking if `expanded` contains `arxiv.org`. Extract the paper ID for use with arxiv MCP tools.
