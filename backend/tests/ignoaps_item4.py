"""Review item 4 (IGNOAPS): a proposal the validator wrongly passed.

`ignoaps_item4.json` is item 4's exact Proposal block from the Extract scheme rules run summary,
unedited (the model's own output: scheme, rule_quotes, benefit_quote). Before the value-type and
paper checks the validator called it valid; its mistakes:
  1. `is_bpl eq "yes"`: the text "yes" is not true, so nobody could ever be eligible.
  2. Six rules on has_<document> fields, quoted from "Documents Required" (papers are not
     eligibility), and all six listed under "fixable".
  3. The residential-proof alternatives ("Voter card/ Electricity Bill/Aadhar Card") all required.
The quotes are real lines of data/scheme_sources/ignoaps.txt.
"""

import copy
import json
from pathlib import Path
from typing import Any

from app.db.seed import DEFAULT_DATA_DIR
from app.pipeline.source import read_source

SOURCE = read_source("ignoaps", DEFAULT_DATA_DIR)
SLUG = SOURCE.slug
SOURCE_URL = SOURCE.url
SOURCE_TEXT = SOURCE.text

BENEFIT_TEXT = "A monthly pension of ₹ 200 up to 79 years and ₹ 500 thereafter."
BENEFIT_QUOTE = BENEFIT_TEXT

# The papers item 4 wrote rules for, in rule order (rules 2 to 7).
PAPER_RULES = [
    "domicile_certificate",
    "voter_id",
    "aadhaar_card",
    "birth_certificate",
    "bank_account_aadhaar_linked",
    "ration_card",
]


def proposal() -> dict[str, Any]:
    """Item 4 exactly as the model wrote it."""
    text = (Path(__file__).parent / "ignoaps_item4.json").read_text(encoding="utf-8")
    return json.loads(text)  # type: ignore[no-any-return]


def corrected() -> dict[str, Any]:
    """Item 4 with only its three mistakes fixed, nothing else changed: BPL as is_true, the paper
    rules gone (the papers stay in documents), nothing fixable, the alternatives not required and a
    note saying so. This is what the new checks must accept."""
    fixed = copy.deepcopy(proposal())
    version = fixed["scheme"]["version"]
    version["rules"]["all"] = [
        {"field": "is_bpl", "op": "is_true"},
        version["rules"]["all"][1],  # age gte 60
    ]
    version["rules"]["fixable"] = []
    fixed["rule_quotes"] = fixed["rule_quotes"][:2]
    for document in version["documents"]:
        if document["code"] in (
            "voter_id",
            "aadhaar_card",
        ):  # "Voter card/ Electricity Bill/ Aadhar Card"
            document["required"] = False
    fixed["scheme"]["labeller_notes"]["notes"] = [
        "Residential proof: any one of voter card, electricity bill or Aadhaar card; none required."
    ]
    return fixed


def build(
    rules_and_quotes: list[tuple[dict[str, Any], str]], *, benefit: bool = True
) -> dict[str, Any]:
    """A small proposal for one-off cases, on the real source text: item 4's scheme and papers
    (none of the alternatives required) with the given (rule, quote) pairs."""
    answer = copy.deepcopy(corrected())
    version = answer["scheme"]["version"]
    version["rules"] = {"all": [rule for rule, _ in rules_and_quotes], "fixable": []}
    answer["rule_quotes"] = [{"index": i, "quote": q} for i, (_, q) in enumerate(rules_and_quotes)]
    if not benefit:
        version["benefit_text_en"] = None
        answer["benefit_quote"] = None
    return answer
