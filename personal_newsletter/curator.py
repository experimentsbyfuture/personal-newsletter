"""Turn a pile of candidate articles into a personalized newsletter.

Two curators are available:

- ClaudeCurator: uses the Claude API to pick the stories that actually match the
  subscriber's stated interests and write plain-language summaries.
- HeuristicCurator: no-API fallback that scores by recency and keyword overlap,
  so the pipeline still works without a key (used for demos/tests too).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import List

import anthropic

from .models import Article, Newsletter, NewsletterItem, NewsletterSection, Subscriber

logger = logging.getLogger(__name__)

MODEL = "claude-opus-4-8"
# Cap the candidate pool so the prompt stays a predictable size.
MAX_CANDIDATES = 60

SYSTEM_PROMPT = """\
You are the editor of a one-person newsletter. You receive a subscriber profile and a
list of candidate articles, and you produce a short personalized digest.

Editorial rules:
- Pick only stories that genuinely match this subscriber's topics and stated interests.
  Fewer great picks beat many mediocre ones. Never pad to reach a count.
- Group picks into sections by theme (usually the subscriber's topics). Skip a topic
  entirely if nothing good came in for it.
- Summaries are 2-3 sentences of plain language. No jargon unless the subscriber's
  interests show they're technical. Never invent facts beyond the provided title/summary.
- "Why it matters" is one sentence tailored to THIS subscriber, not a generic claim.
- Use each article's exact url and source as given. Do not fabricate or alter links.
- Write a specific subject line about the actual top stories, not "Your Weekly Digest".
- Keep the overall tone warm and human, like a smart friend forwarding links.
"""


def _profile_block(subscriber: Subscriber) -> str:
    lines = [
        f"Name: {subscriber.name}",
        f"Topics: {', '.join(subscriber.topics)}",
        f"Maximum total stories: {subscriber.max_items}",
    ]
    if subscriber.interests:
        lines.append(f"Interests in their own words: {subscriber.interests}")
    return "\n".join(lines)


def _articles_block(articles: List[Article]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        published = a.published.strftime("%Y-%m-%d") if a.published else "unknown date"
        lines.append(
            f"[{i}] topic={a.topic} | source={a.source} | published={published}\n"
            f"    title: {a.title}\n"
            f"    url: {a.url}\n"
            f"    summary: {a.summary or '(none provided)'}"
        )
    return "\n".join(lines)


class ClaudeCurator:
    """LLM-backed curation and summarization."""

    def __init__(self, client: anthropic.Anthropic | None = None):
        self.client = client or anthropic.Anthropic()

    def curate(self, subscriber: Subscriber, articles: List[Article]) -> Newsletter:
        candidates = articles[:MAX_CANDIDATES]
        response = self.client.messages.parse(
            model=MODEL,
            max_tokens=16000,
            thinking={"type": "adaptive"},
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Subscriber profile:\n"
                        f"{_profile_block(subscriber)}\n\n"
                        f"Candidate articles ({len(candidates)}):\n"
                        f"{_articles_block(candidates)}\n\n"
                        "Produce this subscriber's newsletter."
                    ),
                }
            ],
            output_format=Newsletter,
        )
        newsletter = response.parsed_output
        if newsletter is None:
            raise RuntimeError("Claude returned output that did not match the Newsletter schema")
        return newsletter


class HeuristicCurator:
    """Keyword/recency fallback used when no API key is available."""

    def curate(self, subscriber: Subscriber, articles: List[Article]) -> Newsletter:
        interest_words = {
            w.lower().strip(".,")
            for w in subscriber.interests.split()
            if len(w) > 3
        }

        def score(article: Article) -> float:
            s = 0.0
            if article.published:
                age_days = (datetime.now(timezone.utc) - article.published).total_seconds() / 86400
                s += max(0.0, 7 - age_days)
            text = f"{article.title} {article.summary}".lower()
            s += 2.0 * sum(1 for w in interest_words if w in text)
            return s

        by_topic: dict[str, List[Article]] = defaultdict(list)
        for article in articles:
            by_topic[article.topic].append(article)

        per_topic = max(1, subscriber.max_items // max(1, len(subscriber.topics)))
        sections = []
        for topic in subscriber.topics:
            picks = sorted(by_topic.get(topic, []), key=score, reverse=True)[:per_topic]
            if not picks:
                continue
            sections.append(
                NewsletterSection(
                    heading=topic.replace("-", " ").title(),
                    items=[
                        NewsletterItem(
                            title=a.title,
                            url=a.url,
                            source=a.source,
                            summary=a.summary[:280] or a.title,
                            why_it_matters=f"Matches your interest in {topic}.",
                        )
                        for a in picks
                    ],
                )
            )

        top = sections[0].items[0].title if sections and sections[0].items else "your topics"
        return Newsletter(
            subject=f"Your digest: {top}",
            greeting=f"Hi {subscriber.name},",
            intro=(
                "Here's what's new across "
                f"{', '.join(subscriber.topics)} — picked by recency and keyword match. "
                "(Set ANTHROPIC_API_KEY for smarter curation.)"
            ),
            sections=sections,
            sign_off="See you next time!",
        )


def get_curator(use_llm: bool = True):
    """Pick the best available curator, falling back gracefully without a key."""
    if not use_llm:
        return HeuristicCurator()
    try:
        client = anthropic.Anthropic()
        # The SDK resolves keys from env or an `ant auth login` profile; if neither
        # exists, constructing the request would fail — probe cheaply via auth headers.
        if client.api_key is None and client.auth_token is None:
            raise anthropic.AnthropicError("no credentials")
        return ClaudeCurator(client)
    except Exception:
        logger.warning("No Anthropic credentials found - falling back to heuristic curation")
        return HeuristicCurator()
