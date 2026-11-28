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

A web page also has a tab bar: the tab names in a row (Details, Benefits, Eligibility, ...) with no
text between them. Pasted as text it looks like six headings in a row, and the page text after it
would land under the last one. A run of TAB_BAR_LENGTH or more headings in a row, with nothing but
blank lines between them, is that bar: it is ignored, not read as headings and not as content.
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


# Three headings in a row with no text between them is a tab bar. Two can be a real page whose
# first section is empty.
TAB_BAR_LENGTH = 3


def _bare_heading(line: str) -> str | None:
    """The heading word if the line is only a heading ("FAQ: the question" is a heading with text,
    so it is never part of a tab bar), else None."""
    text = " ".join(line.split()).lower().rstrip(":").strip()
    return text if text in HEADINGS else None


def _bar_part(run: list[tuple[int, str]]) -> list[int]:
    """The line positions of a run of headings that are the tab bar. A tab name that comes round a
    second time starts the real headings (the page repeats "Details" right after the bar), so the
    bar stops there."""
    seen: set[str] = set()
    bar: list[int] = []
    for position, name in run:
        if name in seen:
            break
        seen.add(name)
        bar.append(position)
    return bar


def _tab_bar_lines(lines: list[str]) -> set[int]:
    """Positions of the lines that make up a tab bar (see the module text)."""
    ignored: set[int] = set()
    run: list[tuple[int, str]] = []
    for position, line in enumerate([*lines, "x"]):  # the extra non-heading line ends the last run
        if not line.strip():
            continue  # blank lines do not break a run
        name = _bare_heading(line)
        if name is not None:
            run.append((position, name))
            continue
        bar = _bar_part(run)
        if len(bar) >= TAB_BAR_LENGTH:
            ignored.update(bar)
        run = []
    return ignored


def split_sections(text: str) -> dict[str, str]:
    """Heading (lower case) -> the text under it. A heading that appears twice joins its texts.
    A tab bar (a run of headings with no text between them) is left out."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    lines = text.splitlines()
    tab_bar = _tab_bar_lines(lines)
    for position, line in enumerate(lines):
        if position in tab_bar:
            continue
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


# Where a rule's quote may come from. Details, Eligibility and Exclusions state who the scheme is
# for and who is left out (PM-KISAN's exclusions are real conditions); a paper list (Documents
# Required) or a how-to-apply text (Application Process) does not, even when it happens to contain
# words like "Aadhaar" or "BPL".
RULE_QUOTE_SECTIONS = ("details", "eligibility", "eligibility criteria", "exclusions")


def rule_quote_text(text: str) -> str | None:
    """The text a rule quote may come from: Details, Eligibility and Exclusions ('' if the source
    has headings but none of them). None when the source has no headings at all (a press release,
    a PDF): then there is nothing to tell the sections apart by, and the whole text is the only
    thing to check."""
    sections = split_sections(text)
    if not sections:
        return None
    return "\n".join(sections[name] for name in RULE_QUOTE_SECTIONS if name in sections)


def sections_containing(text: str, quote: str) -> list[str]:
    """Names of the sections whose text holds `quote` (whitespace ignored), in page order."""
    wanted = squash(quote)
    return [name for name, body in split_sections(text).items() if wanted in squash(body)]


_SPACES = re.compile(r"\s+")


def squash(text: str) -> str:
    """Whitespace collapsed to single spaces, so a quote matches across a line break."""
    return _SPACES.sub(" ", text).strip()
