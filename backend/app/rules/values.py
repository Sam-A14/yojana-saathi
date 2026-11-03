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
    """A yearly household income range in rupees. upper is None for the open-ended top band."""

    lower: int
    upper: int | None


# Cut at income limits that real schemes use (1, 2, 2.5, 3, 5 and 8 lakh). A family only tells us
# the band, so the true income is somewhere between the edges; the eligibility step must not
# pretend it knows more (docs/decisions/009, added with that step).
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
