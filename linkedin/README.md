# LinkedIn System

This folder supports a human-reviewed LinkedIn workflow for visibility,
networking, and relationship building during a job search.

It never posts, comments, likes, follows, connects, or messages automatically.
It only creates private review queues and draft text.

## Workflow

1. Add manual raw ideas to `ideas.md`.
2. Run idea generation to mine your private story bank for public-safe themes.
3. Run draft generation once a week to create posts from unused raw ideas.
4. Run discovery two or three times per week to find people, posts, and
   networking message drafts for manual review.
5. Publish manually on LinkedIn and log results in `published.md`.

## Local Commands

```bash
PYTHONPATH=scripts python scripts/linkedin/generate_ideas.py
PYTHONPATH=scripts python scripts/linkedin/draft_posts.py
PYTHONPATH=scripts python scripts/linkedin/discover_engagement.py
```

All generated content requires human review before use.
