"""The one list of facts a rule may talk about.

Why a strict list: a typo in a rule ("grup_d", "govt_employe") must be an error the moment the rule
is read, not a silent "unknown" for every family. data/scheme.schema.json repeats the field names
for the labelling stage; tests/test_seed_files.py fails if the two lists drift apart.

Some fields are yes/no. Their value is True, False, or missing/None. Missing means "the family has
not told us yet", and the engine turns that into "unknown", never into "no".
"""

# Facts about one person. Any member of the household may be asked about these.
MEMBER_FIELDS = frozenset(
    {
        "age",
        "gender",
        "marital_status",
        "occupation",
        "education",
        "is_student",
        "disability",
        "owns_cultivable_land",
        "paid_income_tax_last_year",
        "govt_employee",
        "pension_band",
        "is_registered_professional",
        "holds_constitutional_post",
        "is_remarried",
    }
)

# Facts about the household as a whole. The same for every member.
HOUSEHOLD_FIELDS = frozenset({"state", "district", "area_type", "income_band_max", "category"})

ATTRIBUTE_FIELDS = MEMBER_FIELDS | HOUSEHOLD_FIELDS

# "has_<document code>" fields (has_land_record, ...) are member facts too: one yes/no per document.
# Which codes exist is data (data/documents.json), so the engine only checks the prefix; a test
# checks the codes against the file.
DOCUMENT_FIELD_PREFIX = "has_"

# Fields with a fixed set of answers. Rules and database CHECK constraints share these tuples.
GOVT_EMPLOYEE_VALUES = ("none", "group_d", "other")
PENSION_BAND_VALUES = ("none", "below_10k", "10k_plus")

ALLOWED_VALUES: dict[str, tuple[str, ...]] = {
    "govt_employee": GOVT_EMPLOYEE_VALUES,
    "pension_band": PENSION_BAND_VALUES,
}


def is_known_field(name: str) -> bool:
    return name in ATTRIBUTE_FIELDS or name.startswith(DOCUMENT_FIELD_PREFIX)


def is_household_field(name: str) -> bool:
    return name in HOUSEHOLD_FIELDS
