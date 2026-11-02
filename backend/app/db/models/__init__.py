# Importing every model here registers all tables on Base.metadata, which Alembic relies on.
from app.db.models.catalogue import Document, Scheme, SchemeDocument, SchemeVersion
from app.db.models.family import Household, Member, MemberDocument, User
from app.db.models.outputs import Alert, EligibilityResult, ReviewItem

__all__ = [
    "Alert",
    "Document",
    "EligibilityResult",
    "Household",
    "Member",
    "MemberDocument",
    "ReviewItem",
    "Scheme",
    "SchemeDocument",
    "SchemeVersion",
    "User",
]
