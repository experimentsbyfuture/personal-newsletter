"""Command-line interface.

Commands:
    newsletter topics                      List topics available in the feed catalog
    newsletter preview [--subscriber X]    Build newsletters and write HTML previews to ./out
    newsletter send [--subscriber X]       Build and email newsletters via SMTP
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import config
from .curator import get_curator
from .fetcher import fetch_articles, load_sample_articles
from .models import Subscriber
from .renderer import render_html, render_text
from .sender import SenderConfigError, send_email

logger = logging.getLogger("personal_newsletter")


def _slug(name: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")


def _select_subscribers(args) -> list[Subscriber]:
    subscribers = config.load_subscribers(args.subscribers)
    if args.subscriber:
        wanted = args.subscriber.lower()
        subscribers = [
            s for s in subscribers
            if s.name.lower() == wanted or s.email.lower() == wanted
        ]
        if not subscribers:
            sys.exit(f"No subscriber named '{args.subscriber}' in {args.subscribers}")
    return subscribers


def _build(args, subscriber: Subscriber, catalog) -> tuple[str, str, str]:
    """Fetch, curate, and render for one subscriber. Returns (subject, html, text)."""
    if args.sample:
        articles = load_sample_articles(subscriber.topics)
    else:
        articles = fetch_articles(catalog, subscriber.topics, max_age_days=args.max_age_days)
    if not articles:
        raise RuntimeError(
            f"No articles found for {subscriber.name}'s topics ({', '.join(subscriber.topics)})"
        )
    print(f"  {len(articles)} candidate articles for {subscriber.name}")
    curator = get_curator(use_llm=not args.no_llm)
    newsletter = curator.curate(subscriber, articles)
    return newsletter.subject, render_html(newsletter, subscriber), render_text(newsletter, subscriber)


def cmd_topics(args) -> None:
    catalog = config.load_feed_catalog(args.feeds)
    for topic in sorted(catalog):
        print(f"{topic}  ({len(catalog[topic])} feeds)")


def cmd_preview(args) -> None:
    catalog = config.load_feed_catalog(args.feeds)
    subscribers = _select_subscribers(args)
    for warning in config.validate_topics(subscribers, catalog):
        print(f"warning: {warning}", file=sys.stderr)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    for subscriber in subscribers:
        print(f"Building newsletter for {subscriber.name}...")
        try:
            subject, html_body, text_body = _build(args, subscriber, catalog)
        except RuntimeError as exc:
            print(f"  skipped: {exc}", file=sys.stderr)
            continue
        html_path = out_dir / f"{_slug(subscriber.name)}.html"
        html_path.write_text(html_body)
        (out_dir / f"{_slug(subscriber.name)}.txt").write_text(text_body)
        print(f"  subject: {subject}")
        print(f"  preview: {html_path}")


def cmd_send(args) -> None:
    catalog = config.load_feed_catalog(args.feeds)
    subscribers = _select_subscribers(args)
    for warning in config.validate_topics(subscribers, catalog):
        print(f"warning: {warning}", file=sys.stderr)

    for subscriber in subscribers:
        print(f"Building newsletter for {subscriber.name}...")
        try:
            subject, html_body, text_body = _build(args, subscriber, catalog)
        except RuntimeError as exc:
            print(f"  skipped: {exc}", file=sys.stderr)
            continue
        try:
            send_email(subscriber, subject, html_body, text_body)
        except SenderConfigError as exc:
            sys.exit(str(exc))
        print(f"  sent '{subject}' to {subscriber.email}")


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        prog="newsletter",
        description="Personalized newsletters curated per subscriber.",
    )
    parser.add_argument("--feeds", default=config.DEFAULT_FEEDS_FILE, help="Feed catalog YAML")
    parser.add_argument(
        "--subscribers", default=config.DEFAULT_SUBSCRIBERS_FILE, help="Subscribers YAML"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("topics", help="List available topics")

    for name, help_text in [
        ("preview", "Write HTML/text previews to a directory"),
        ("send", "Send newsletters via SMTP"),
    ]:
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--subscriber", help="Only this subscriber (name or email)")
        p.add_argument("--max-age-days", type=int, default=7, help="Ignore older articles")
        p.add_argument("--no-llm", action="store_true", help="Use heuristic curation (no API key)")
        p.add_argument("--sample", action="store_true", help="Use bundled sample articles (offline)")
        if name == "preview":
            p.add_argument("--out", default="out", help="Output directory")

    args = parser.parse_args(argv)
    {"topics": cmd_topics, "preview": cmd_preview, "send": cmd_send}[args.command](args)


if __name__ == "__main__":
    main()
