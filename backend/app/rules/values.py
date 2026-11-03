"""Answer lists for the family questions the API accepts.

One place, so the API, the tests and (later) the setup form agree. These are deliberately NOT added
to rules/fields.py ALLOWED_VALUES: that list also makes the engine reject rule values outside it,
and changing what a stored scheme rule may say is a bigger decision than what a family may answer.
"""

from dataclasses import dataclass

# "unmarried" (not "single") because that is the word the seed schemes and test profiles use.
MARITAL_STATUS_VALUES = ("unmarried", "married", "widow", "divorced", "separated")
CATEGORY_VALUES = ("General", "SC", "ST", "OBC")
EDUCATION_VALUES = (
    "none",
    "primary",
    "secondary",
    "senior_secondary",
    "graduate",
    "postgraduate",
)
OCCUPATION_VALUES = (
    "farmer",
    "agricultural_labourer",
    "student",
    "homemaker",
    "self_employed",
    "private_job",
    "government_job",
    "retired",
    "unemployed",
    "other",
)


@dataclass(frozen=True)
class IncomeBand:
    """A yearly household income range in rupees: MORE than `lower`, up to and including `upper`.

    So "1_to_2_lakh" is 100001 to 200000 rupees, and a rule cut at exactly 100000 or 200000 has a
    definite answer for it. The first band also includes 0. `upper` is None for the open-ended top
    band. Incomes are whole rupees, so "more than lower" means `lower + 1` at the least.
    """

    lower: int
    upper: int | None

    @property
    def lowest(self) -> int:
        """The smallest income that falls in this band."""
        return 0 if self.lower == 0 else self.lower + 1


# Cut at income limits that real schemes use (1, 2, 2.5, 3, 5 and 8 lakh). A family only tells us
# the band, so the true income is somewhere inside it; the eligibility step must not pretend it
# knows more (docs/decisions/009).
INCOME_BANDS: dict[str, IncomeBand] = {
    "up_to_1_lakh": IncomeBand(0, 100_000),
    "1_to_2_lakh": IncomeBand(100_000, 200_000),
    "2_to_2_5_lakh": IncomeBand(200_000, 250_000),
    "2_5_to_3_lakh": IncomeBand(250_000, 300_000),
    "3_to_5_lakh": IncomeBand(300_000, 500_000),
    "5_to_8_lakh": IncomeBand(500_000, 800_000),
    "above_8_lakh": IncomeBand(800_000, None),
}
INCOME_BAND_VALUES = tuple(INCOME_BANDS)

# Documents one person holds for the whole family. If any member has one, every member counts as
# having it (see api/facts.py). The one place to add a code when a new family-level document
# appears; a test checks that each code exists in data/documents.json.
HOUSEHOLD_DOCUMENT_CODES = frozenset({"ration_card", "bpl_card", "family_register"})
