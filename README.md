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

## Use it as a Claude Skill (no install, no server, no API key)

Anyone with Claude can get their own personal newsletter straight from this
repo — their Claude does the searching and curating, on their subscription:

```
/plugin marketplace add experimentsbyfuture/personal-newsletter
/plugin install personal-newsletter@personal-newsletter
```

Then ask for `/personal-newsletter:news` (or just say "give me my news
digest"). The first run interviews you — topics, interests in your own words,
how many stories — and saves a profile at `~/.personal-newsletter/profile.md`.
Every run after that is a fresh, personalized digest. Say "no more crypto" or
"more science" any time and it updates your profile.

Prefer a bare skill instead of a plugin? Copy the folder:

```bash
cp -r plugins/personal-newsletter/skills/news ~/.claude/skills/
# then: /news
```

For an automatic daily edition, schedule it — e.g. a Claude Code routine, or
a cron entry running `claude -p "/news"`.

Everything below is the standalone pipeline for *emailing* newsletters to
other people (subscribers who don't use Claude).

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

`newsletter send` picks a backend automatically:

**Resend (recommended — free tier, one API call):**

```bash
export RESEND_API_KEY=re_...
export FROM_EMAIL="Your Newsletter <news@yourdomain.com>"  # verified in Resend
newsletter send
```

**Plain SMTP:**

```bash
export SMTP_HOST=smtp.example.com SMTP_PORT=587
export SMTP_USER=you@example.com SMTP_PASSWORD=...
export FROM_EMAIL="Your Newsletter <you@example.com>"
newsletter send
```

## Daily delivery (zero servers)

The repo ships a GitHub Actions workflow
(`.github/workflows/daily-newsletter.yml`) that emails every subscriber once a
day. To turn it on, add three repository secrets under **Settings → Secrets
and variables → Actions**:

| Secret | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic API key |
| `RESEND_API_KEY` | free key from [resend.com](https://resend.com) |
| `FROM_EMAIL` | a sender verified in Resend |

Then use the workflow's **Run workflow** button for a test send. Adjust the
cron in the workflow file to change the delivery time.

## Curation

Curators are tried in order, so the pipeline always works with whatever you have:

1. **Claude API** — with `ANTHROPIC_API_KEY` set, curation runs on
   `claude-opus-4-8` using structured outputs, so the newsletter always comes
   back as a validated schema (subject, intro, sections, per-story summary +
   "why it matters").
2. **No API key needed** — if the [`claude` CLI](https://claude.com/claude-code)
   is installed and logged in (covered by a Claude Pro/Max subscription), the
   same curation runs through it automatically. No per-token billing.
3. **No Claude at all** — a heuristic curator (recency + keyword match against
   the subscriber's interests) keeps everything functional; pass `--no-llm` to
   force it.

## Development

```bash
pip install -e ".[dev]"
pytest
```
