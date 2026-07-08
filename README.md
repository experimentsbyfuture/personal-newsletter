# Personal Newsletter

Instead of subscribing to someone else's newsletter full of jargon and stories you
don't care about, each person defines the topics and interests **they** care about —
and gets a digest curated and summarized just for them.

## How it works

```
feeds.yaml (topic → RSS feeds)          subscribers.yaml (who wants what)
            \                                /
             fetch fresh articles per topic
                        |
        Claude curates + summarizes per subscriber
     (picks only what matches their stated interests,
      writes plain-language summaries + "why it matters")
                        |
          HTML email → preview locally or send via SMTP
```

## Quick start

```bash
pip install -e .

# See it work immediately with bundled sample articles (no network, no API key):
newsletter preview --sample --no-llm
open out/alex.html

# Real run: fetch live RSS feeds and let Claude curate
export ANTHROPIC_API_KEY=sk-ant-...
newsletter preview
```

## Configure

**`feeds.yaml`** — the topic catalog. Add any topic and the RSS/Atom feeds that cover it:

```yaml
topics:
  ai:
    - https://www.technologyreview.com/topic/artificial-intelligence/feed
```

**`subscribers.yaml`** — who gets a newsletter and what they care about. The
free-text `interests` field is what makes it personal — the curator uses it to
filter out noise, match tone, and explain *why each story matters to this person*:

```yaml
subscribers:
  - name: Alex
    email: alex@example.com
    topics: [ai, technology]
    interests: >
      Software engineer. Loves open-source AI and developer tools; not
      interested in funding rounds or crypto.
    max_items: 6
```

## Commands

| Command | What it does |
|---|---|
| `newsletter topics` | List topics available in the catalog |
| `newsletter preview` | Build newsletters, write HTML + text previews to `./out` |
| `newsletter preview --subscriber Alex` | Preview for one subscriber only |
| `newsletter send` | Build and email newsletters via SMTP |

Useful flags: `--sample` (bundled offline articles), `--no-llm` (heuristic
curation without an API key), `--max-age-days N` (freshness window).

## Sending email

`newsletter send` uses SMTP, configured via environment variables:

```bash
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USER=you@example.com
export SMTP_PASSWORD=...
export FROM_EMAIL="Your Newsletter <you@example.com>"
newsletter send
```

To deliver on a schedule, run `newsletter send` from cron / GitHub Actions
(e.g. `0 7 * * MON` for a Monday-morning edition).

## Curation

With `ANTHROPIC_API_KEY` set, curation runs on Claude (`claude-opus-4-8`) using
structured outputs, so the newsletter always comes back as a validated schema
(subject, intro, sections, per-story summary + "why it matters"). Without a key,
a heuristic curator (recency + keyword match against the subscriber's interests)
keeps the pipeline fully functional.

## Development

```bash
pip install -e ".[dev]"
pytest
```
