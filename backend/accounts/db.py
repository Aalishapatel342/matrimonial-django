"""
Thin MongoDB access layer.

Keeps pymongo connection setup in one place so views never talk to
MongoClient directly. One client is reused for the lifetime of the
process (pymongo's client is already connection-pooled internally,
so re-creating it per-request would be wasteful).
"""

from django.conf import settings
from pymongo import MongoClient, ASCENDING

_client = None


def get_client():
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGO_URI)
    return _client


def get_db():
    return get_client()[settings.MONGO_DB_NAME]


def get_users_collection():
    """
    Returns the `users` collection, making sure a unique index exists
    on email and phone so two profiles can never collide — this is
    enforced at the database level, not just in form validation.
    """
    users = get_db()["users"]
    users.create_index([("email", ASCENDING)], unique=True)
    users.create_index([("phone", ASCENDING)], unique=True)
    return users
