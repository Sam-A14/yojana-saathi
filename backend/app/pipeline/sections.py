"""Cut a pasted scheme page into its sections, so a quote can be traced to the one it came from.

Scheme pages (myScheme and similar) are a list of headings, each followed by its text:

    Eligibility
    The applicant should be at least 60 years of age.
    Documents Required
    Ration Card

A heading is a line that is only one of the known words below (case does not matter, a trailing
colon is fine), or a line that starts "FAQ:". Text before the first heading belongs to no section.
A source with no such headings (a press release, a PDF) has no sections at all: nothing in it can
be shown to come from "Eligibility".
"""

import re

HEADINGS = frozenset(
    {
        "details",
        "benefit",
        "benefits",
        "eligibility",
        "eligibility criteria",
        "documents",
        "documents required",
        "documents needed",
        "application process",
        "exclusions",
        "faq",
        "faqs",
        "frequently asked questions",
        "sources and references",
    }
)


def _heading(line: str) -> str | None:
    text = " ".join(line.split()).lower().rstrip(":").strip()
    if text in HEADINGS:
        return text
    return "faq" if " ".join(line.split()).lower().startswith("faq:") else None


def split_sections(text: str) -> dict[str, str]:
    """Heading (lower case) -> the text under it. A heading that appears twice joins its texts."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        heading = _heading(line)
        if heading is not None:
            current = heading
            sections.setdefault(current, [])
            if heading == "faq" and ":" in line:  # "FAQ: the question" is a heading and a line
                sections[current].append(line)
        elif current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines) for name, lines in sections.items()}


def eligibility_text(text: str) -> str:
    """Only what is written under an Eligibility heading ('' if the source has none)."""
    sections = split_sections(text)
    return "\n".join(
        sections[name] for name in ("eligibility", "eligibility criteria") if name in sections
    )


_SPACES = re.compile(r"\s+")


def squash(text: str) -> str:
    """Whitespace collapsed to single spaces, so a quote matches across a line break."""
    return _SPACES.sub(" ", text).strip()
