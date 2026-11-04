"""Utilities for claim evidence file validation and secure pathing."""
import os
import uuid
from django.core.exceptions import ValidationError
from django.utils import timezone

MAX_EVIDENCE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EVIDENCE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}


def claim_evidence_upload_path(instance, filename: str) -> str:
    """Generate collision-resistant, path-traversal-safe upload path for claim evidence."""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EVIDENCE_EXTENSIONS:
        ext = ".bin"
    now = timezone.now()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return os.path.join("claim_evidence", now.strftime("%Y"), now.strftime("%m"), unique_name)


def validate_claim_evidence(file_obj):
    """Enforce size limit and allowed extensions on uploaded ownership verification proof."""
    if not file_obj:
        return

    # 1. Enforce size limit
    if file_obj.size > MAX_EVIDENCE_SIZE_BYTES:
        max_mb = MAX_EVIDENCE_SIZE_BYTES // (1024 * 1024)
        raise ValidationError(f"Evidence file size exceeds the {max_mb} MB limit.")

    # 2. Enforce extension restriction
    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext not in ALLOWED_EVIDENCE_EXTENSIONS:
        allowed = ", ".join(ALLOWED_EVIDENCE_EXTENSIONS)
        raise ValidationError(f"Unsupported evidence file format ({ext}). Allowed formats: {allowed}.")

