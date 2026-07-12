"""accounts.api_profiles

Small helper to keep the /api/profiles/ view logic tidy.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def parse_int(v: Optional[str]) -> Optional[int]:
    if v is None:
        return None
    v = str(v).strip()
    if not v:
        return None
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


from datetime import datetime


def _compute_age_from_dob(dob_value: Any) -> Optional[int]:
    """Compute age (years) from a Mongo `dob` field.

    Accepts common formats:
      - "YYYY-MM-DD" string
      - datetime/date instance
    Returns None if DOB is missing/invalid.
    """
    if dob_value is None:
        return None

    try:
        # datetime/date object
        if hasattr(dob_value, "year") and hasattr(dob_value, "month") and hasattr(dob_value, "day"):
            birth_date = datetime(dob_value.year, dob_value.month, dob_value.day)
        else:
            dob_str = str(dob_value).strip()
            if not dob_str:
                return None
            # Common: YYYY-MM-DD
            birth_date = datetime.strptime(dob_str[:10], "%Y-%m-%d")

        today = datetime.now()
        years = today.year - birth_date.year
        # If birthday hasn't happened yet this year, subtract 1.
        if (today.month, today.day) < (birth_date.month, birth_date.day):
            years -= 1

        if years < 0:
            return None
        return int(years)
    except Exception:
        return None


def _profile_age(profile_doc: Dict[str, Any]) -> int:
    """Return best-effort age for cards."""
    stored_age = profile_doc.get("age")
    try:
        if stored_age not in (None, ""):
            stored_age_i = int(stored_age)
            if stored_age_i > 0:
                return stored_age_i
    except Exception:
        pass

    computed = _compute_age_from_dob(profile_doc.get("dob"))
    return computed if computed is not None else 0


def add_profile_fields(profile_doc: Dict[str, Any], *, compatibility_default: int = 70) -> Dict[str, Any]:
    """Return JSON-serializable profile dict matching dashboard.html expectations."""

    full_name = profile_doc.get("full_name", "")

    compatibility = profile_doc.get("compatibility")
    if compatibility is None:
        compatibility = compatibility_default

    return {
        "id": str(profile_doc.get("_id")),
        "full_name": full_name,
        "age": _profile_age(profile_doc),
        "profession": profile_doc.get("profession", ""),
        "city": profile_doc.get("city", ""),
        "education": profile_doc.get("education", ""),
        "height": profile_doc.get("height", ""),
        "religion": profile_doc.get("religion", ""),
        "mother_tongue": profile_doc.get("mother_tongue", ""),
        "bio": profile_doc.get("bio", ""),
        "verified": bool(profile_doc.get("verified", False)),
        "compatibility": compatibility,
        "wishlisted": bool(profile_doc.get("wishlisted", False)),
        "interested": bool(profile_doc.get("interested", False)),
        "profile_pic": profile_doc.get("profile_pic"),
    }


