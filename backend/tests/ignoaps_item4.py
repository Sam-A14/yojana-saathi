"""Review item 4 (IGNOAPS): a proposal the validator wrongly passed.

RECONSTRUCTED, not copied: the stored JSON lives in the production database and could not be read
from here. It is rebuilt from the real source text (data/scheme_sources/ignoaps.txt; the quotes are
real lines of it) and from the three mistakes the owner found in item 4:
  1. `is_bpl eq "yes"` (the text "yes" is not true: nobody could ever be eligible),
  2. rules on has_<document> fields whose quotes come from "Documents Required",
  3. alternatives ("Voter card/ Electricity Bill/ Aadhar Card") all marked required.
Replace `proposal()` with the real JSON when it is available; the tests depend only on those
defects.
"""

from typing import Any

from app.db.seed import DEFAULT_DATA_DIR
from app.pipeline.source import read_source

SOURCE = read_source("ignoaps", DEFAULT_DATA_DIR)
SLUG = SOURCE.slug
SOURCE_URL = SOURCE.url
SOURCE_TEXT = SOURCE.text

# (rule, quote): the first two quotes are under "Eligibility" in the source, the rest under
# "Documents Required".
RULES_AND_QUOTES: list[tuple[dict[str, Any], str]] = [
    (
        {"field": "age", "op": "gte", "value": 60},
        "The applicant should be at least 60 years of age.",
    ),
    (
        {"field": "is_bpl", "op": "eq", "value": "yes"},  # defect 1
        "The applicant should be living Below Poverty Line.",
    ),
    ({"field": "has_domicile_certificate", "op": "is_true"}, "Domicile Certificate"),  # defect 2
    ({"field": "has_ration_card", "op": "is_true"}, "Ration Card"),
    ({"field": "has_bank_account_aadhaar_linked", "op": "is_true"}, "Bank Passbook"),
    ({"field": "has_aadhaar_card", "op": "is_true"}, "Aadhar Number"),
]

BENEFIT_TEXT = "A monthly pension of ₹200 up to 79 years and ₹500 from 80 years."
BENEFIT_QUOTE = "A monthly pension of ₹ 200 up to 79 years and ₹ 500 thereafter."
# Item 4's text says "from 80 years", but its quote has no 80: the figure came from the FAQ line. A
# quote that shows every figure in the text is this sentence from the FAQ.
CORRECTED_BENEFIT_QUOTE = (
    "is Rs. 200/- per month per beneficiary up to 79 years and Rs.500/- per month per beneficiary "
    "from 80 year onwards"
)


def documents(*, alternatives_required: bool) -> list[dict[str, Any]]:
    """The papers. Defect 3: the residential-proof alternatives (voter card, Aadhaar) required."""
    return [
        {"code": "domicile_certificate", "required": True, "applies_to": "applicant"},
        {"code": "voter_id", "required": alternatives_required, "applies_to": "applicant"},
        {"code": "aadhaar_card", "required": alternatives_required, "applies_to": "applicant"},
        {"code": "ration_card", "required": True, "applies_to": "household"},
        {"code": "bank_account_aadhaar_linked", "required": True, "applies_to": "applicant"},
    ]


def build(
    rules_and_quotes: list[tuple[dict[str, Any], str]],
    *,
    benefit: bool = True,
    benefit_quote: str = BENEFIT_QUOTE,
    **doc_options: Any,
) -> dict[str, Any]:
    return {
        "scheme": {
            "slug": SLUG,
            "name_en": "Indira Gandhi National Old Age Pension Scheme",
            "level": "central",
            "state": None,
            "category": "pension",
            "official_url": SOURCE_URL,
            "version": {
                "rules": {"all": [rule for rule, _ in rules_and_quotes], "fixable": []},
                "benefit_text_en": BENEFIT_TEXT if benefit else None,
                "benefit_text_hi": None,
                "source_url": SOURCE_URL,
                "verified_at": None,
                "approved_by": None,
                "documents": documents(**doc_options),
            },
        },
        "rule_quotes": [{"index": i, "quote": q} for i, (_, q) in enumerate(rules_and_quotes)],
        "benefit_quote": benefit_quote if benefit else None,
    }


def proposal() -> dict[str, Any]:
    """Item 4 as it was: passes the old validator, wrong in the three ways above."""
    return build(RULES_AND_QUOTES, alternatives_required=True)


def corrected() -> dict[str, Any]:
    """What a good extraction looks like: BPL as is_true, papers only in documents, alternatives
    not required. Used to show the new checks flag the defects and nothing else."""
    rules = [
        RULES_AND_QUOTES[0],
        (
            {"field": "is_bpl", "op": "is_true"},
            "The applicant should be living Below Poverty Line.",
        ),
    ]
    return build(rules, alternatives_required=False, benefit_quote=CORRECTED_BENEFIT_QUOTE)
