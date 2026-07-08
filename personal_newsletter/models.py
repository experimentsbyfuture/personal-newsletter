"""Core data models shared across the pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Article(BaseModel):
    """A candidate article fetched from a feed."""

    title: str
    url: str
    source: str
    topic: str
    summary: str = ""
    published: Optional[datetime] = None


class Subscriber(BaseModel):
    """A person receiving a personalized newsletter."""

    name: str
    email: str
    topics: List[str]
    # Free-text description of what they care about, used to steer curation
    # beyond the topic labels (e.g. "prefers open-source AI news, no crypto").
    interests: str = ""
    max_items: int = 8


class NewsletterItem(BaseModel):
    """One curated story in the final newsletter."""

    title: str
    url: str
    source: str
    summary: str = Field(description="2-3 sentence plain-language summary of the story")
    why_it_matters: str = Field(
        description="One sentence on why this specific subscriber should care"
    )


class NewsletterSection(BaseModel):
    """A group of stories under a topic heading."""

    heading: str
    items: List[NewsletterItem]


class Newsletter(BaseModel):
    """The fully curated newsletter for one subscriber."""

    subject: str = Field(description="Email subject line, specific and jargon-free")
    greeting: str = Field(description="One-line personal greeting")
    intro: str = Field(
        description="2-3 sentence overview of what's in this edition and why it was picked"
    )
    sections: List[NewsletterSection]
    sign_off: str = Field(description="Short friendly closing line")
