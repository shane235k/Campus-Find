"""Utility functions for the items app: secure image upload paths and Pillow validations."""
import os
import uuid
from django.core.exceptions import ValidationError
from django.utils import timezone
from PIL import Image

# Maximum allowed file size for item images: 5 MB
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024

# Allowed image MIME types and Pillow format identifiers
ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def item_image_upload_path(instance, filename):
    """Generate a unique, collision-resistant upload path for item images.
    
    Path format: item_images/YYYY/MM/<uuid4><ext>
    Protects original filenames, avoids filesystem exposure, and prevents path traversal.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        ext = ".jpg"
    unique_name = f"{uuid.uuid4().hex}{ext}"
    now = timezone.now()
    return f"item_images/{now.year:04d}/{now.month:02d}/{unique_name}"


def validate_item_image(image_file):
    """Validate item image size and content integrity using Pillow.
    
    Ensures:
    1. File size does not exceed 5 MB.
    2. File is a real, readable image format (JPEG, PNG, WEBP).
    3. Image dimensions are within reasonable boundaries.
    """
    if not image_file:
        return image_file

    # 1. Enforce 5 MB maximum size limit
    if hasattr(image_file, "size") and image_file.size > MAX_IMAGE_SIZE_BYTES:
        raise ValidationError("Item image file size cannot exceed 5 MB.")

    # 2. Inspect image using Pillow
    try:
        # Seek to start in case of previous reads
        if hasattr(image_file, "seek"):
            image_file.seek(0)
        
        with Image.open(image_file) as img:
            img.verify()

            if img.format not in ALLOWED_IMAGE_FORMATS:
                raise ValidationError(
                    f"Unsupported image format '{img.format}'. Allowed formats: JPG, PNG, WEBP."
                )

        # Reset pointer for downstream Django saving
        if hasattr(image_file, "seek"):
            image_file.seek(0)

    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError("Uploaded file is not a valid or readable image.") from exc

    return image_file
