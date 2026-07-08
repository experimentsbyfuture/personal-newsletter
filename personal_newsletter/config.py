"""Loading of the topic catalog and subscriber list from YAML files."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

from .models import Subscriber

DEFAULT_FEEDS_FILE = "feeds.yaml"
DEFAULT_SUBSCRIBERS_FILE = "subscribers.yaml"


class ConfigError(Exception):
    pass


def load_feed_catalog(path: str | Path = DEFAULT_FEEDS_FILE) -> Dict[str, List[str]]:
    """Load the topic -> feed URLs catalog.

    Format:
        topics:
          ai:
            - https://example.com/feed.xml
    """
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Feed catalog not found: {path}")
    data = yaml.safe_load(path.read_text()) or {}
    topics = data.get("topics")
    if not isinstance(topics, dict) or not topics:
        raise ConfigError(f"{path} must contain a non-empty 'topics' mapping")
    catalog: Dict[str, List[str]] = {}
    for topic, feeds in topics.items():
        if not isinstance(feeds, list) or not all(isinstance(f, str) for f in feeds):
            raise ConfigError(f"Topic '{topic}' must map to a list of feed URLs")
        catalog[str(topic).lower()] = feeds
    return catalog


def load_subscribers(path: str | Path = DEFAULT_SUBSCRIBERS_FILE) -> List[Subscriber]:
    """Load subscribers and validate their topics."""
    path = Path(path)
    if not path.exists():
        raise ConfigError(f"Subscribers file not found: {path}")
    data = yaml.safe_load(path.read_text()) or {}
    raw = data.get("subscribers")
    if not isinstance(raw, list) or not raw:
        raise ConfigError(f"{path} must contain a non-empty 'subscribers' list")
    subscribers = []
    for entry in raw:
        sub = Subscriber(**entry)
        sub.topics = [t.lower() for t in sub.topics]
        subscribers.append(sub)
    return subscribers


def validate_topics(subscribers: List[Subscriber], catalog: Dict[str, List[str]]) -> List[str]:
    """Return warnings for subscriber topics that have no feeds in the catalog."""
    warnings = []
    for sub in subscribers:
        for topic in sub.topics:
            if topic not in catalog:
                warnings.append(
                    f"Subscriber '{sub.name}' wants topic '{topic}' which has no feeds "
                    f"in the catalog (available: {', '.join(sorted(catalog))})"
                )
    return warnings
