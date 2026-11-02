"""Made-up scheme text and a matching, correct model answer, shared by the pipeline tests.

The scheme here is invented for tests. It is not a real scheme and is never loaded anywhere.
"""

import copy
import json
from typing import Any

SLUG = "test-scheme"
SOURCE_URL = "https://example.org/test-scheme"

SOURCE_TEXT = """\
Test Scheme for Senior Citizens
The scheme gives a pension to every person aged 60 years or above.
Only persons belonging to SC or ST
categories can apply.
A family where any member paid income tax last year is not eligible.
"""

QUOTES = [
    "aged 60 years or above",
    "belonging to SC or ST categories",
    "any member paid income tax last year",
]


def good_answer() -> dict[str, Any]:
    """A model answer that passes every check against SOURCE_TEXT."""
    return {
        "scheme": {
            "slug": SLUG,
            "name_en": "Test Scheme",
            "level": "central",
            "state": None,
            "category": "pension",
            "official_url": SOURCE_URL,
            "version": {
                "rules": {
                    "all": [
                        {"field": "age", "op": "gte", "value": 60},
                        {"field": "category", "op": "in", "value": ["SC", "ST"]},
                        {
                            "not": {
                                "any_member": {
                                    "field": "paid_income_tax_last_year",
                                    "op": "is_true",
                                }
                            }
                        },
                    ],
                    "fixable": [],
                },
                "source_url": SOURCE_URL,
                "verified_at": None,
                "approved_by": None,
                "documents": [],
            },
        },
        "rule_quotes": [{"index": i, "quote": q} for i, q in enumerate(QUOTES)],
    }


def answer_text(answer: dict[str, Any]) -> str:
    return json.dumps(copy.deepcopy(answer))
