"""Fetch candidate articles from RSS/Atom feeds for a set of topics."""

from __future__ import annotations

import html
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from importlib import resources
from typing import Dict, Iterable, List
from urllib.parse import urlparse

import feedparser

from .models import Article

logger = logging.getLogger(__name__)

TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return html.unescape(TAG_RE.sub("", text or "")).strip()


def _parse_entry_time(entry) -> datetime | None:
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            return datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
    return None


def _source_name(feed, feed_url: str) -> str:
    title = getattr(getattr(feed, "feed", None), "title", "") or ""
    return title.strip() or urlparse(feed_url).netloc


def fetch_feed(feed_url: str, topic: str, max_entries: int = 15) -> List[Article]:
    """Fetch one feed and normalize its entries into Articles."""
    parsed = feedparser.parse(feed_url)
    if parsed.bozo and not parsed.entries:
        logger.warning("Could not parse feed %s: %s", feed_url, parsed.get("bozo_exception"))
        return []
    source = _source_name(parsed, feed_url)
    articles = []
    for entry in parsed.entries[:max_entries]:
        link = getattr(entry, "link", "")
        title = _strip_html(getattr(entry, "title", ""))
        if not link or not title:
            continue
        articles.append(
            Article(
                title=title,
                url=link,
                source=source,
                topic=topic,
                summary=_strip_html(getattr(entry, "summary", ""))[:600],
                published=_parse_entry_time(entry),
            )
        )
    return articles


def fetch_articles(
    catalog: Dict[str, List[str]],
    topics: Iterable[str],
    max_age_days: int = 7,
    max_workers: int = 8,
) -> List[Article]:
    """Fetch all feeds for the given topics in parallel, dedupe, and sort by recency."""
    jobs = [
        (feed_url, topic)
        for topic in topics
        for feed_url in catalog.get(topic, [])
    ]
    articles: List[Article] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_feed, url, topic): url for url, topic in jobs}
        for future in as_completed(futures):
            try:
                articles.extend(future.result())
            except Exception as exc:  # a broken feed should never sink the run
                logger.warning("Feed %s failed: %s", futures[future], exc)

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
    seen_urls: set[str] = set()
    fresh: List[Article] = []
    for article in articles:
        if article.url in seen_urls:
            continue
        seen_urls.add(article.url)
        if article.published and article.published < cutoff:
            continue
        fresh.append(article)

    fresh.sort(key=lambda a: a.published or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return fresh


def load_sample_articles(topics: Iterable[str]) -> List[Article]:
    """Bundled sample articles for offline demos and tests."""
    raw = resources.files("personal_newsletter").joinpath("data/sample_articles.json").read_text()
    wanted = {t.lower() for t in topics}
    return [
        Article(**item)
        for item in json.loads(raw)
        if item["topic"] in wanted
    ]
