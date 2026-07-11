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


def add_profile_fields(profile_doc: Dict[str, Any], *, compatibility_default: int = 70) -> Dict[str, Any]:
    """Return JSON-serializable profile dict matching dashboard.html expectations."""

    full_name = profile_doc.get("full_name", "")

    compatibility = profile_doc.get("compatibility")
    if compatibility is None:
        compatibility = compatibility_default

    return {
        "id": str(profile_doc.get("_id")),
        "full_name": full_name,
        "age": profile_doc.get("age", 0),
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

