"""
Strict relevance filter for CoS / Founder's Office roles.
Used by all scrapers to ensure only real, senior, paid roles pass through.
"""

# Title must contain at least one of these
REQUIRED_KEYWORDS = [
    "chief of staff",
    "chief-of-staff",
    "founder's office",
    "founder office",
    "founders office",
    "head of staff",
]

# Title must NOT contain any of these
BLOCKED_KEYWORDS = [
    "intern",          # intern, internship
    "co-founder",
    "co founder",
    "cofounder",
    "technical co",
    "executive assistant",
    " ea to ",
    "mba student",
    "mba intern",
    "student",
    "assistant department",
    "assistant manager",
    "department manager",
    "administrative chief",    # "Administrative Chief of Staff, Office of CHRO"
    "ceo/founder",
    "cto/founder",
    "coo/founder",
    "/ founder",               # catches "CEO / Founder" patterns
    "analyst",                 # junior analyst roles
    "fresher",
    "entry level",
    "equity based",
    "equity only",
    "volunteer",
    "freelance",
    "part-time",
    "part time",
]

# Company / role patterns to skip (too junior or wrong function)
BLOCKED_TITLE_PATTERNS = [
    "executive assistant",
    "personal assistant",
    "office admin",
    "office manager",
    "operations intern",
    "strategy intern",
]


def is_relevant(title: str) -> bool:
    """
    Returns True only if the title is a genuine CoS / Founder's Office role.
    Strict: must match a required keyword AND not match any blocked keyword.
    """
    t = title.lower().strip()

    # Must contain a required keyword
    if not any(kw in t for kw in REQUIRED_KEYWORDS):
        return False

    # Must not contain a blocked keyword
    if any(kw in t for kw in BLOCKED_KEYWORDS):
        return False

    return True


def classify_position(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["founder's office", "founder office", "founders office"]):
        return "Founder's Office"
    return "Chief of Staff"
