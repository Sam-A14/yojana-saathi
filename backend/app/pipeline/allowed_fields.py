"""The exact list of facts a proposed rule may use."""

import json
from pathlib import Path

from app.rules.fields import ATTRIBUTE_FIELDS, DOCUMENT_FIELD_PREFIX


def allowed_fields(data_dir: Path) -> list[str]:
    """Member/household attributes from rules/fields.py plus one has_<code> per known document.

    fields.py only knows the has_ prefix (document codes are data), so the codes come from
    documents.json. That is stricter than the engine, on purpose: a made-up document code in a
    proposal is a mistake to flag, not a rule to publish.
    """
    documents = json.loads((data_dir / "documents.json").read_text(encoding="utf-8"))["documents"]
    document_fields = sorted(DOCUMENT_FIELD_PREFIX + d["code"] for d in documents)
    return sorted(ATTRIBUTE_FIELDS) + document_fields


def allowed_documents(data_dir: Path) -> list[tuple[str, str]]:
    """(code, English name) for every document in documents.json, in the file's order.

    The same file that makes the has_<code> fields, so the codes a proposal may put in
    `version.documents` and the fields it may use in rules cannot drift apart.
    """
    documents = json.loads((data_dir / "documents.json").read_text(encoding="utf-8"))["documents"]
    return [(d["code"], d["name_en"]) for d in documents]
