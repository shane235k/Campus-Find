"""Database models for ownership claims and administrative verification workflow."""
import uuid
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from .utils import claim_evidence_upload_path, validate_claim_evidence


class ClaimStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Review"
    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"


class Claim(models.Model):
    """Formal ownership claim submitted by a student for a misplaced or found item."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    claimant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="submitted_claims",
        help_text="Student filing the ownership claim.",
    )
    item = models.ForeignKey(
        "items.Item",
        on_delete=models.CASCADE,
        related_name="claims",
        help_text="The campus report being claimed.",
    )
    potential_match = models.ForeignKey(
        "matching.PotentialMatch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claims",
        help_text="Optional AI match candidate linking this claim.",
    )

    # Narrative and Private Verification Answers (strictly hidden from public item listings)
    claim_description = models.TextField(
        help_text="Claimant's description of how the item was lost and ownership circumstances.",
    )
    distinguishing_features = models.TextField(
        help_text="Private features: secret scratches, stickers, engravings, serial number, or passwords.",
    )
    item_contents = models.TextField(
        blank=True,
        default="",
        help_text="Detailed inventory of contents inside bag, wallet, or notebook (if applicable).",
    )
    last_seen_details = models.TextField(
        blank=True,
        default="",
        help_text="Specific timestamp, room number, or area where the claimant last had the item.",
    )
    evidence_file = models.FileField(
        upload_to=claim_evidence_upload_path,
        validators=[validate_claim_evidence],
        blank=True,
        null=True,
        help_text="Optional proof of purchase, warranty card, receipt, or matching photo (max 5 MB).",
    )

    # Verification State
    status = models.CharField(
        max_length=20,
        choices=ClaimStatus.choices,
        default=ClaimStatus.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_claims",
        help_text="Staff administrator who verified or reviewed this claim.",
    )
    admin_notes = models.TextField(
        blank=True,
        default="",
        help_text="Internal staff investigation notes, strictly hidden from student view.",
    )
    rejection_reason = models.TextField(
        blank=True,
        default="",
        help_text="Reason for rejection communicated to the claimant.",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ownership Claim"
        verbose_name_plural = "Ownership Claims"
        ordering = ["-created_at"]
        constraints = [
            # A student cannot submit multiple concurrent active claims for the same item
            models.UniqueConstraint(
                fields=["claimant", "item"],
                condition=Q(status__in=[ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW]),
                name="unique_active_claim_per_claimant_item",
            ),
            # An item can have at most one APPROVED claim
            models.UniqueConstraint(
                fields=["item"],
                condition=Q(status=ClaimStatus.APPROVED),
                name="unique_approved_claim_per_item",
            ),
        ]

    def clean(self):
        super().clean()
        # Item reporter cannot submit claim for their own report
        if self.item_id and self.claimant_id and self.item.reported_by_id == self.claimant_id:
            raise ValidationError("You cannot submit an ownership claim for an item you reported yourself.")
        
        # Cannot submit claim if item is already resolved or closed
        if self.item_id and self._state.adding:
            if self.item.status in ["RESOLVED", "CLOSED"]:
                raise ValidationError(f"This item is {self.item.get_status_display().lower()} and can no longer be claimed.")

        # Cannot submit concurrent active claim if one already exists
        if self.item_id and self.claimant_id and self.is_active:
            existing_active = Claim.objects.filter(
                claimant_id=self.claimant_id,
                item_id=self.item_id,
                status__in=[ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW],
            )
            if not self._state.adding and self.pk:
                existing_active = existing_active.exclude(pk=self.pk)
            if existing_active.exists():
                raise ValidationError("You already have an active claim pending for this item.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Claim #{str(self.id)[:8]} by {self.claimant.username} for [{self.item.title}] ({self.status})"

    @property
    def is_pending(self) -> bool:
        return self.status == ClaimStatus.PENDING

    @property
    def is_under_review(self) -> bool:
        return self.status == ClaimStatus.UNDER_REVIEW

    @property
    def is_active(self) -> bool:
        return self.status in [ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW]

    @property
    def is_approved(self) -> bool:
        return self.status == ClaimStatus.APPROVED

    @property
    def is_rejected(self) -> bool:
        return self.status == ClaimStatus.REJECTED

    @property
    def is_withdrawn(self) -> bool:
        return self.status == ClaimStatus.WITHDRAWN

    def can_withdraw(self, user) -> bool:
        """Determines if the given user is authorized to withdraw this claim."""
        if not user or not user.is_authenticated:
            return False
        return self.claimant == user and self.is_active
