from django.core.management.base import BaseCommand
from accounts.db import get_db

class Command(BaseCommand):
    help = "Create MongoDB indexes"

    def handle(self, *args, **options):
        db = get_db()

        # Ensure collections exist (idempotent)
        for name in ["interests", "subscriptions", "phonepe_otp_challenges"]:
            if name not in db.list_collection_names():
                db.create_collection(name)
                
        # Interests unique compound index
        db.interests.create_index([("from_user_id", 1), ("to_user_id", 1)], unique=True)

        # Premium subscriptions: one subscription doc per user
        db.subscriptions.create_index([("user_id", 1)], unique=True)

        # PhonePe OTP challenge: enable quick lookup + expiry sweeps
        db.phonepe_otp_challenges.create_index([("user_id", 1), ("expires_at", 1)])
        db.phonepe_otp_challenges.create_index([("expires_at", 1)])

        self.stdout.write(self.style.SUCCESS("MongoDB indexes created."))
