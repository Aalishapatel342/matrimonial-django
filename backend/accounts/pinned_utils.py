"""Internal helpers for pinned-profile feature.

Kept separate only to avoid cluttering views.py with formatting logic.
"""

from bson import ObjectId
from .db import get_users_collection


def format_profile_card(profile_doc, score=None, interested=None):
    """Return a JSON-serializable dict matching the dashboard modal/card fields."""
    if not profile_doc:
        return None

    full_name = profile_doc.get("full_name", "")
    compatibility = score
    if compatibility is None:
        compatibility = 75 + (sum(ord(c) for c in full_name) % 24)

    data = {
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
        "profile_pic_is_profile_pic": bool(profile_doc.get("profile_pic_is_profile_pic")),
        "verified": profile_doc.get("verified", False),
        "compatibility": compatibility,
        "interested": bool(interested),
        "profile_pic": (
            bool(profile_doc.get("profile_pic_is_profile_pic"))
            and profile_doc.get("profile_pic_content_type")
            and profile_doc.get("profile_pic")
        )
        and (
            "data:" + profile_doc.get("profile_pic_content_type") + ";base64," + profile_doc.get("profile_pic")
        )
        or None,
    }
    return data

