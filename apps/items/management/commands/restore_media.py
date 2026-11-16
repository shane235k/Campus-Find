import os
import base64
from django.conf import settings
from django.core.management.base import BaseCommand
from apps.items.models import StoredImage


class Command(BaseCommand):
    help = "Restores all item images from the database onto the local filesystem."

    def handle(self, *args, **options):
        target_dir = os.path.join(settings.MEDIA_ROOT, "item_images")
        os.makedirs(target_dir, exist_ok=True)

        images = StoredImage.objects.all()
        if not images.exists():
            self.stdout.write(self.style.WARNING("No StoredImage records found in the database."))
            return

        restored_count = 0
        skipped_count = 0

        for stored in images:
            file_path = os.path.join(target_dir, stored.filename)
            if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
                skipped_count += 1
                continue

            try:
                data = base64.b64decode(stored.image_base64)
                with open(file_path, "wb") as f:
                    f.write(data)
                self.stdout.write(self.style.SUCCESS(f"Restored: {stored.filename} ({len(data)} bytes)"))
                restored_count += 1
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"Failed to restore {stored.filename}: {exc}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Media restore complete. Restored: {restored_count}, Existing/Skipped: {skipped_count}."
            )
        )
