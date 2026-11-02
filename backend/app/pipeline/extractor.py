"""Source text -> LLM -> validated proposal. Does not touch the database."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.db.seed import DEFAULT_DATA_DIR, _validator
from app.llm.base import LLMClient
from app.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from app.pipeline.allowed_fields import allowed_fields
from app.pipeline.source import SourceDocument
from app.pipeline.validator import ValidationResult, validate_output

# Low, not zero: we want the same rules every run, but not a stuck loop on an odd sentence.
EXTRACTION_TEMPERATURE = 0.1


@dataclass(frozen=True)
class Extraction:
    source: SourceDocument
    model: str
    raw_output: str  # exactly what the model sent, kept even when it is unusable
    validation: ValidationResult


def extract(
    source: SourceDocument, client: LLMClient, data_dir: Path = DEFAULT_DATA_DIR
) -> Extraction:
    schema_path = data_dir / "scheme.schema.json"
    schema: dict[str, Any] = json.loads(schema_path.read_text(encoding="utf-8"))
    fields = allowed_fields(data_dir)

    prompt = build_user_prompt(
        slug=source.slug,
        source_url=source.url,
        source_text=source.text,
        fields=fields,
        schema=schema,
    )
    raw = client.complete_json(
        system=SYSTEM_PROMPT, prompt=prompt, temperature=EXTRACTION_TEMPERATURE
    )
    validation = validate_output(
        raw,
        slug=source.slug,
        source_url=source.url,
        source_text=source.text,
        allowed=fields,
        schema_validator=_validator(schema_path),
    )
    return Extraction(source=source, model=client.model, raw_output=raw, validation=validation)
