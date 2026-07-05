from django.core.management.base import BaseCommand
from accounts.db import get_db

class Command(BaseCommand):
    help = "Create MongoDB indexes"

    def handle(self, *args, **options):
        db = get_db()
        # create collection (if not exists)
        db.create_collection("interests")
        # create unique compound index
        db.interests.create_index([("from_user_id", 1), ("to_user_id", 1)], unique=True)
        self.stdout.write(self.style.SUCCESS("MongoDB indexes created."))