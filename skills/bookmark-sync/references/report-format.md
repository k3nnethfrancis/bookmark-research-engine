# Deep Dive Report Format

Every report in `shoshin-codex/bookmarks/reports/` follows this structure.

## Frontmatter

```yaml
---
title: "Descriptive Title"
date: YYYY-MM-DD
categories:
  - multi-agent-orchestration       # pick from canonical slugs
  - rl-training-methods
tier: 1                             # 1 or 2, from triage
sources:
  - url: "https://..."
    type: paper                     # paper | blog | tweet | github | video
  - url: "https://..."
    type: tweet
tags:
  - specific-tag                    # freeform, specific to this report
  - another-tag
status: unread                      # unread → read → referenced
triage_date: "YYYY-MM-DD"
---
```

## Canonical Category Slugs

Use these exactly:
- `multi-agent-orchestration`
- `rl-training-methods`
- `ai-safety-alignment-monitoring`
- `behavioral-measurement-llm-psychology`
- `ai-research-automation`
- `novel-architectures-paradigms`
- `agent-tooling-developer-experience`

## Body Sections

```markdown
# {Title}

## Source
- Tweet: {url}
- Paper: {url if found}
- Blog: {url if found}
- GitHub: {url if found}

## Key Findings
{Bullet points of concrete findings — be specific, cite numbers and methods.
 This is the most important section. No fluff.}

## Methodology (if applicable)
{How they tested/built this — datasets, evaluation methods, baselines.
 Skip if source is a tweet thread without formal methodology.}

## Implications for Helm
{Specific ways this informs multi-agent observation/control research.
 Connect to concrete Helm concepts: judging dimensions, trace features,
 orchestration patterns, training pipeline, observation layer.}

## Implications for Sigmund
{Specific ways this informs behavioral profiling / AI co-scientist training.
 Connect to behavioral measurement, profiling dimensions, training signals.}

## Actionable Takeaways
{What Kenneth should DO with this information — be concrete.
 "Read section X" > "interesting paper".
 "Prototype detection for pattern Y" > "relevant to our work".}

## Open Questions
{What remains unknown or needs follow-up.
 Genuinely open — not restated findings as questions.}
```

## Filename Convention

Slugified: lowercase, hyphens instead of spaces, no special characters.

Examples:
- `when-multi-agent-helps-vs-hurts.md`
- `goodfire-interp-scaled-rl.md`
- `agent-failure-taxonomy-7-patterns.md`
