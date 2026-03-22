#!/bin/bash
# List pending bookmarks with author, text snippet, and link count
# Uses bre config for pending file location

if ! command -v bre &>/dev/null; then
    echo "bre CLI not found. Run: pip install bookmark-research-engine"
    exit 1
fi

# Get pending file path from bre config
PENDING=$(python3 -c "from bre.config import load_config; print(load_config().pending_file)" 2>/dev/null)

if [ -z "$PENDING" ] || [ ! -f "$PENDING" ]; then
    echo "No pending bookmarks file found. Run 'bre fetch' first."
    exit 1
fi

python3 -c "
import json, sys

with open('$PENDING') as f:
    data = json.load(f)

bookmarks = data.get('bookmarks', [])
if not bookmarks:
    print('No pending bookmarks.')
    sys.exit(0)

print(f'=== {len(bookmarks)} Pending Bookmarks ===')
print()

for i, b in enumerate(bookmarks, 1):
    author = b.get('author', '?')
    text = b.get('text', '')[:150].replace('\n', ' ')
    if len(b.get('text', '')) > 150:
        text += '...'
    links = b.get('links', [])
    link_count = len(links) if isinstance(links, list) else 0

    arxiv_ids = []
    if isinstance(links, list):
        for link in links:
            expanded = link.get('expanded', '') if isinstance(link, dict) else ''
            if 'arxiv.org' in expanded:
                parts = expanded.split('/')
                for j, p in enumerate(parts):
                    if p in ('abs', 'pdf') and j + 1 < len(parts):
                        arxiv_ids.append(parts[j + 1].replace('.pdf', ''))

    arxiv_tag = f' [arxiv: {\" \".join(arxiv_ids)}]' if arxiv_ids else ''
    print(f'{i}. @{author} ({link_count} links{arxiv_tag})')
    print(f'   {text}')
    print()
"
