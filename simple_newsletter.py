"""The simplest possible personal newsletter: one Claude call, no RSS plumbing.

Claude's built-in web search finds this week's stories for the subscriber's
topics, curates against their stated interests, and writes the newsletter as
a complete HTML email. Run it, open the file, done.

    export ANTHROPIC_API_KEY=sk-ant-...
    python simple_newsletter.py
"""

from datetime import date
from pathlib import Path

import anthropic

# ── The entire "database": who gets a newsletter and what they care about ──
SUBSCRIBERS = [
    {
        "name": "Alex",
        "topics": ["AI", "developer tools"],
        "interests": (
            "Software engineer. Loves open-source AI and developer tools; "
            "not interested in company funding rounds or crypto."
        ),
    },
]

PROMPT = """\
You are the editor of a personal newsletter for one subscriber.

Subscriber: {name}
Topics: {topics}
Their interests, in their own words: {interests}

Search the web for notable stories from the past 7 days on their topics.
Pick the 5-7 stories that best match their stated interests — skip anything
they said they don't care about. For each story write a 2-3 sentence
plain-language summary, a one-line "why it matters to you", and link the
original source.

Respond with ONLY a complete, self-contained HTML email document (inline CSS,
max-width 640px, clean and readable). Include a specific subject line as the
<title> and top heading, a short personal intro, the stories, and a warm
sign-off. No markdown, no commentary outside the HTML.
"""

client = anthropic.Anthropic()
out_dir = Path("out")
out_dir.mkdir(exist_ok=True)

for sub in SUBSCRIBERS:
    print(f"Building newsletter for {sub['name']}...")
    with client.messages.stream(
        model="claude-opus-4-8",
        max_tokens=64000,
        thinking={"type": "adaptive"},
        tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}],
        messages=[
            {
                "role": "user",
                "content": PROMPT.format(
                    name=sub["name"],
                    topics=", ".join(sub["topics"]),
                    interests=sub["interests"],
                ),
            }
        ],
    ) as stream:
        message = stream.get_final_message()

    html = "".join(block.text for block in message.content if block.type == "text")
    # Strip a markdown code fence if the model wrapped the HTML in one.
    if html.strip().startswith("```"):
        html = html.strip().strip("`").removeprefix("html").strip()

    path = out_dir / f"{sub['name'].lower()}-{date.today().isoformat()}.html"
    path.write_text(html)
    print(f"  wrote {path}")
