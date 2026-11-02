"""Reading the scheme text a person pasted into data/scheme_sources/<slug>.txt."""

import re
from dataclasses import dataclass
from pathlib import Path

from app.db.seed import DEFAULT_DATA_DIR

# The same pattern as scheme slugs. It also keeps "../" out of the file path we build from it.
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
# A scheme page is a few thousand words. Anything far bigger is probably the wrong paste.
MAX_SOURCE_CHARS = 100_000


class SourceError(Exception):
    """The input file is missing or malformed. Fixed by editing the file, not by retrying."""


@dataclass(frozen=True)
class SourceDocument:
    slug: str
    url: str
    text: str


def read_source(slug: str, data_dir: Path = DEFAULT_DATA_DIR) -> SourceDocument:
    if not SLUG_PATTERN.fullmatch(slug):
        raise SourceError(f"'{slug}' is not a valid slug (lowercase words joined by '-').")
    path = data_dir / "scheme_sources" / f"{slug}.txt"
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise SourceError(f"Cannot read {path.name} in data/scheme_sources/: {error}") from error

    first_line, _, body = content.partition("\n")
    url = first_line.strip()
    if not re.match(r"^https?://\S+$", url):
        raise SourceError(f"{path.name}: line 1 must be the source URL (http:// or https://).")
    text = body.strip()
    if not text:
        raise SourceError(f"{path.name}: there is no scheme text after the URL line.")
    if len(text) > MAX_SOURCE_CHARS:
        raise SourceError(f"{path.name}: text is longer than {MAX_SOURCE_CHARS} characters.")
    return SourceDocument(slug=slug, url=url, text=text)
