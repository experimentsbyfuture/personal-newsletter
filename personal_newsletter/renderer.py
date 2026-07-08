"""Render a curated Newsletter into email-ready HTML and plain text."""

from __future__ import annotations

from datetime import date

from jinja2 import Environment, PackageLoader

from .models import Newsletter, Subscriber

_env = Environment(
    loader=PackageLoader("personal_newsletter", "templates"),
    autoescape=True,
)


def render_html(newsletter: Newsletter, subscriber: Subscriber) -> str:
    template = _env.get_template("newsletter.html.j2")
    return template.render(
        newsletter=newsletter,
        subscriber=subscriber,
        date=date.today().strftime("%B %d, %Y"),
    )


def render_text(newsletter: Newsletter, subscriber: Subscriber) -> str:
    """Plain-text alternative part for email clients that prefer it."""
    lines = [newsletter.subject, "=" * len(newsletter.subject), "", newsletter.greeting, "", newsletter.intro, ""]
    for section in newsletter.sections:
        lines += [section.heading.upper(), "-" * len(section.heading), ""]
        for item in section.items:
            lines += [
                f"* {item.title} ({item.source})",
                f"  {item.url}",
                f"  {item.summary}",
                f"  Why it matters: {item.why_it_matters}",
                "",
            ]
    lines.append(newsletter.sign_off)
    return "\n".join(lines)
