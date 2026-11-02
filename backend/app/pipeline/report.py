"""Markdown for the GitHub Actions run summary: the proposal, its validity, and its accuracy."""

import json
import re

from app.pipeline.extractor import Extraction


def _fence(text: str, language: str = "") -> str:
    """Wrap text in a code fence that the text itself cannot close.

    The model's output is untrusted; inside a code block it is shown, never rendered as links.
    """
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    ticks = "`" * max(3, longest + 1)
    return f"{ticks}{language}\n{text}\n{ticks}"


def render_report(extraction: Extraction, saved_note: str, accuracy: str | None) -> str:
    validation = extraction.validation
    lines = [
        f"## Extract scheme rules: {extraction.source.slug}",
        "",
        f"- Source: {extraction.source.url}",
        f"- Model: {extraction.model}",
        f"- {saved_note}",
        "- Nothing is published. A person must review the proposal first.",
        "",
    ]
    if validation.is_valid:
        lines.append("### Validation: passed")
    else:
        lines.append(f"### Validation: FAILED ({len(validation.problems)} problems)")
        lines.append("The proposal was kept and flagged. It is not dropped.")
        lines.append("")
        for problem in validation.problems:
            lines.append(f"- `{problem.code}` at `{problem.where}`: {problem.message}")
    lines.append("")

    lines.append("### Accuracy against the hand-labelled seed file")
    if accuracy is None:
        seed = f"data/schemes_seed/{extraction.source.slug}.json"
        lines.append(f"No seed file `{seed}`, so no score.")
    else:
        lines.append(_fence(accuracy, "text"))
    lines.append("")

    lines.append("### Proposal")
    if validation.scheme is None:
        lines.append("The model's answer could not be read as a proposal. Raw text:")
        lines.append(_fence(extraction.raw_output))
    else:
        proposal = {"scheme": validation.scheme, "rule_quotes": validation.quotes}
        lines.append(_fence(json.dumps(proposal, indent=2, ensure_ascii=False), "json"))
    return "\n".join(lines) + "\n"
