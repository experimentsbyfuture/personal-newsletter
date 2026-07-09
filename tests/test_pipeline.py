"""Offline tests for config loading, heuristic curation, and rendering."""

import textwrap

import pytest

from personal_newsletter import config
from personal_newsletter.curator import HeuristicCurator
from personal_newsletter.fetcher import load_sample_articles
from personal_newsletter.models import Subscriber
from personal_newsletter.renderer import render_html, render_text


@pytest.fixture
def subscriber():
    return Subscriber(
        name="Alex",
        email="alex@example.com",
        topics=["ai", "technology"],
        interests="open-source AI and developer tools",
        max_items=4,
    )


def test_load_feed_catalog(tmp_path):
    feeds = tmp_path / "feeds.yaml"
    feeds.write_text(
        textwrap.dedent(
            """
            topics:
              AI:
                - https://example.com/feed.xml
            """
        )
    )
    catalog = config.load_feed_catalog(feeds)
    assert catalog == {"ai": ["https://example.com/feed.xml"]}


def test_load_feed_catalog_rejects_empty(tmp_path):
    feeds = tmp_path / "feeds.yaml"
    feeds.write_text("topics: {}")
    with pytest.raises(config.ConfigError):
        config.load_feed_catalog(feeds)


def test_load_subscribers_normalizes_topics(tmp_path):
    subs = tmp_path / "subscribers.yaml"
    subs.write_text(
        textwrap.dedent(
            """
            subscribers:
              - name: Alex
                email: alex@example.com
                topics: [AI, Technology]
            """
        )
    )
    loaded = config.load_subscribers(subs)
    assert loaded[0].topics == ["ai", "technology"]


def test_validate_topics_flags_unknown():
    subs = [Subscriber(name="A", email="a@example.com", topics=["nonexistent"])]
    warnings = config.validate_topics(subs, {"ai": []})
    assert len(warnings) == 1
    assert "nonexistent" in warnings[0]


def test_sample_articles_filtered_by_topic(subscriber):
    articles = load_sample_articles(subscriber.topics)
    assert articles
    assert {a.topic for a in articles} <= set(subscriber.topics)


def test_heuristic_curator_respects_topics_and_limits(subscriber):
    articles = load_sample_articles(["ai", "technology", "science"])
    newsletter = HeuristicCurator().curate(subscriber, articles)
    assert newsletter.sections
    headings = {s.heading.lower() for s in newsletter.sections}
    assert "science" not in headings  # not one of the subscriber's topics
    total_items = sum(len(s.items) for s in newsletter.sections)
    assert 0 < total_items <= subscriber.max_items


def test_render_html_and_text(subscriber):
    articles = load_sample_articles(subscriber.topics)
    newsletter = HeuristicCurator().curate(subscriber, articles)
    html = render_html(newsletter, subscriber)
    text = render_text(newsletter, subscriber)
    first_item = newsletter.sections[0].items[0]
    assert first_item.url in html
    assert newsletter.subject in html
    assert first_item.title in text


def test_render_escapes_html(subscriber):
    articles = load_sample_articles(subscriber.topics)
    articles[0].title = '<script>alert("x")</script>'
    newsletter = HeuristicCurator().curate(subscriber, articles)
    html = render_html(newsletter, subscriber)
    assert "<script>" not in html


def test_send_email_prefers_resend(monkeypatch, subscriber):
    from personal_newsletter import sender

    sent = {}

    def fake_urlopen(request, timeout=None):
        import json as _json

        sent.update(_json.loads(request.data))
        sent["auth"] = request.get_header("Authorization")

        class Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return Resp()

    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("FROM_EMAIL", "News <news@example.com>")
    monkeypatch.setattr(sender.urllib.request, "urlopen", fake_urlopen)

    sender.send_email(subscriber, "Hello", "<p>hi</p>", "hi")
    assert sent["to"] == ["alex@example.com"]
    assert sent["subject"] == "Hello"
    assert sent["auth"] == "Bearer re_test"


def test_send_email_smtp_requires_config(monkeypatch, subscriber):
    from personal_newsletter import sender

    for var in ("RESEND_API_KEY", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "FROM_EMAIL"):
        monkeypatch.delenv(var, raising=False)
    with pytest.raises(sender.SenderConfigError):
        sender.send_email(subscriber, "Hello", "<p>hi</p>", "hi")
