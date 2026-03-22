#!/bin/bash
# List pending bookmarks with author, text snippet, and link count
# Output is structured for easy triage

PENDING="$HOME/Desktop/lab/projects/reference/smaug/.state/pending-bookmarks.json"

if [ ! -f "$PENDING" ]; then
    echo "No pending bookmarks file found at $PENDING"
    exit 1
fi

python3 -c "
import json, sys

with open('$PENDING') as f:
    data = json.load(f)

bookmarks = data.get('bookmarks', data) if isinstance(data, dict) else data
if isinstance(bookmarks, dict):
    bookmarks = bookmarks.get('bookmarks', [])

if not bookmarks:
    print('No pending bookmarks.')
    sys.exit(0)

print(f'=== {len(bookmarks)} Pending Bookmarks ===')
print()

for i, b in enumerate(bookmarks, 1):
    author = b.get('author', b.get('username', '?'))
    text = b.get('text', b.get('tweet_text', b.get('content', '')))
    # Truncate to first 150 chars
    snippet = text[:150].replace('\n', ' ')
    if len(text) > 150:
        snippet += '...'
    links = b.get('links', b.get('urls', []))
    link_count = len(links) if isinstance(links, list) else 0

    # Check for arxiv links
    has_arxiv = False
    arxiv_ids = []
    if isinstance(links, list):
        for link in links:
            expanded = ''
            if isinstance(link, dict):
                expanded = link.get('expanded', link.get('url', ''))
            elif isinstance(link, str):
                expanded = link
            if 'arxiv.org' in expanded:
                has_arxiv = True
                parts = expanded.split('/')
                for j, p in enumerate(parts):
                    if p in ('abs', 'pdf') and j + 1 < len(parts):
                        arxiv_ids.append(parts[j + 1].replace('.pdf', ''))

    arxiv_tag = ''
    if has_arxiv:
        arxiv_tag = f' [arxiv: {\" \".join(arxiv_ids)}]'

    print(f'{i}. @{author} ({link_count} links{arxiv_tag})')
    print(f'   {snippet}')
    print()
"
