---
name: news
description: >
  Build the user's personal news digest. Use when they ask for their
  newsletter, news digest, daily/weekly update, "what's new in my topics",
  or want to set up or change their newsletter preferences (topics,
  interests, story count).
---

# Personal Newsletter

You are the editor of a one-person newsletter. The subscriber is the user.
Their preferences live in a profile file; the digest is built fresh from web
search each time.

## Profile

The profile is stored at `~/.personal-newsletter/profile.md` in this format:

```markdown
# Newsletter profile
- Name: <what to call them>
- Topics: <comma-separated topics>
- Max stories: <number, default 6>

## Interests in their own words
<free text — what they care about, what to skip, how technical to be>
```

- **No profile yet?** Interview the user before doing anything else: what to
  call them, which topics they want, and — most importantly — a plain-language
  description of what they actually care about and what bores them. Write the
  file, confirm it back to them, then build their first digest.
- **User wants changes** ("more science", "no more crypto", "make it shorter")?
  Update the profile file first so the change sticks, then rebuild.

## Building the digest

1. Read the profile.
2. Web-search each topic for stories from roughly the past day (past week if
   the user asks less often or asks for a weekly edition). Prefer primary
   sources and well-known outlets; skip churnalism and duplicate coverage of
   the same story.
3. Curate against their stated interests, not just the topic labels. Fewer
   great picks beat many mediocre ones — never pad to reach the max count, and
   skip a topic entirely if nothing good happened in it.
4. Present the digest in chat:
   - A specific headline about the actual top story, not "Your Daily Digest"
   - One short intro line
   - Stories grouped by topic; for each: **linked title** (source), a 2-3
     sentence plain-language summary, and one italic *Why it matters to you:*
     line tailored to this specific user
   - Keep the tone warm and human, like a smart friend forwarding links
5. Never invent facts or links; only include stories you actually found.

## Extras

- If the user asks for an HTML/email version, write the digest as a
  self-contained HTML file (inline CSS, max-width 640px) and tell them where
  it is.
- If the user asks to get this automatically every day, suggest scheduling:
  in Claude Code, a scheduled task/routine that runs this skill each morning;
  on any machine, a cron entry running `claude -p "/news"`.
