"""Service layer for atomic ownership claim verification, state transitions, and notifications."""
import logging
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.items.models import Item
from apps.matching.models import PotentialMatch, MatchStatus
from apps.notifications.models import Notification, create_notification
from .models import Claim, ClaimStatus

logger = logging.getLogger(__name__)


def submit_claim(
    claimant,
    item: Item,
    claim_description: str,
    distinguishing_features: str,
    item_contents: str = "",
    last_seen_details: str = "",
    evidence_file=None,
    potential_match: PotentialMatch = None,
) -> Claim:
    """Submit and initialize a new ownership claim atomically."""
    with transaction.atomic():
        # Check that item is claimable
        if item.status in [Item.ItemStatus.RESOLVED, Item.ItemStatus.CLOSED]:
            raise ValidationError(f"This item is {item.get_status_display().lower()} and cannot be claimed.")

        if item.reported_by == claimant:
            raise ValidationError("You cannot submit an ownership claim for an item you reported yourself.")

        # Check existing active claim by this claimant
        existing_active = Claim.objects.filter(
            claimant=claimant,
            item=item,
            status__in=[ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW],
        ).first()
        if existing_active:
            raise ValidationError(
                f"You already have an active claim (#{str(existing_active.id)[:8]}) pending for this item."
            )

        # Create Claim
        claim = Claim.objects.create(
            claimant=claimant,
            item=item,
            potential_match=potential_match,
            claim_description=claim_description,
            distinguishing_features=distinguishing_features,
            item_contents=item_contents,
            last_seen_details=last_seen_details,
            evidence_file=evidence_file,
            status=ClaimStatus.PENDING,
        )

        # Advance Item status to CLAIM_PENDING
        if item.status == Item.ItemStatus.OPEN:
            item.status = Item.ItemStatus.CLAIM_PENDING
            item.save(update_fields=["status", "updated_at"])

        # Update PotentialMatch if provided
        if potential_match:
            potential_match.status = MatchStatus.CLAIMED
            potential_match.save(update_fields=["status", "updated_at"])

        # Dispatch notifications
        # 1. Notify claimant
        create_notification(
            recipient=claimant,
            title="Ownership Claim Submitted",
            message=f"Your claim for '{item.title}' has been submitted and is pending staff review.",
            notification_type=Notification.NotificationType.CLAIM_SUBMITTED,
            target_url=f"/claims/{claim.id}/",
        )

        # 2. Notify item reporter
        if item.reported_by and item.reported_by != claimant:
            create_notification(
                recipient=item.reported_by,
                title="New Ownership Claim Filed",
                message=f"A student has submitted an ownership claim for your report '{item.title}'. Campus staff will review the evidence.",
                notification_type=Notification.NotificationType.CLAIM_SUBMITTED,
                target_url=f"/items/{item.id}/",
            )

        logger.info(f"Claim #{claim.id} submitted by {claimant.username} for Item {item.id}")
        return claim


def mark_claim_under_review(claim: Claim, reviewer, admin_notes: str = "") -> Claim:
    """Move a claim to UNDER_REVIEW state."""
    with transaction.atomic():
        if claim.status != ClaimStatus.PENDING:
            raise ValidationError(f"Cannot move claim from {claim.status} to UNDER_REVIEW.")

        claim.status = ClaimStatus.UNDER_REVIEW
        claim.reviewed_by = reviewer
        if admin_notes:
            claim.admin_notes = admin_notes
        claim.save(update_fields=["status", "reviewed_by", "admin_notes", "updated_at"])

        create_notification(
            recipient=claim.claimant,
            title="Claim Under Investigation",
            message=f"Your ownership claim for '{claim.item.title}' is now actively under review by campus desk staff.",
            notification_type=Notification.NotificationType.CLAIM_UNDER_REVIEW,
            target_url=f"/claims/{claim.id}/",
        )
        return claim


def approve_claim(claim: Claim, reviewer, admin_notes: str = "") -> Claim:
    """Atomically approve claim, resolve the item, and reject competing claims."""
    with transaction.atomic():
        # Lock item row to prevent race conditions
        item = Item.objects.select_for_update().get(id=claim.item_id)

        # 1. Verify item is not already resolved
        if item.status == Item.ItemStatus.RESOLVED:
            already_approved = Claim.objects.filter(item=item, status=ClaimStatus.APPROVED).first()
            raise ValidationError(
                f"Item has already been resolved with approved claim #{str(already_approved.id)[:8]}."
            )

        now = timezone.now()

        # 2. Approve selected claim
        claim.status = ClaimStatus.APPROVED
        claim.reviewed_by = reviewer
        claim.resolved_at = now
        if admin_notes:
            claim.admin_notes = admin_notes
        claim.save(update_fields=["status", "reviewed_by", "resolved_at", "admin_notes", "updated_at"])

        # 3. Mark Item as RESOLVED
        item.status = Item.ItemStatus.RESOLVED
        item.save(update_fields=["status", "updated_at"])

        # 4. Mark associated PotentialMatch as VERIFIED
        if claim.potential_match:
            match = claim.potential_match
            match.status = MatchStatus.VERIFIED
            match.save(update_fields=["status", "updated_at"])

        # 5. Automatically reject competing active claims for this item
        competing_claims = Claim.objects.filter(
            item=item,
            status__in=[ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW],
        ).exclude(id=claim.id)

        for comp_claim in competing_claims:
            comp_claim.status = ClaimStatus.REJECTED
            comp_claim.reviewed_by = reviewer
            comp_claim.resolved_at = now
            comp_claim.rejection_reason = (
                "Another claim for this item was verified and approved by campus administration."
            )
            comp_claim.save(update_fields=["status", "reviewed_by", "resolved_at", "rejection_reason", "updated_at"])

            # Notify competing claimant
            create_notification(
                recipient=comp_claim.claimant,
                title="Claim Update: Item Reunited with Verified Owner",
                message=f"Your claim for '{item.title}' was closed because another student's ownership proof was verified.",
                notification_type=Notification.NotificationType.CLAIM_REJECTED,
                target_url=f"/claims/{comp_claim.id}/",
            )

        # 6. Notifications for approved claimant & reporter
        create_notification(
            recipient=claim.claimant,
            title="Ownership Verified & Claim Approved!",
            message=f"Congratulations! Your ownership claim for '{item.title}' has been APPROVED. Please visit the campus recovery desk to collect your belongings.",
            notification_type=Notification.NotificationType.CLAIM_APPROVED,
            target_url=f"/claims/{claim.id}/",
        )

        if item.reported_by and item.reported_by != claim.claimant:
            create_notification(
                recipient=item.reported_by,
                title="Item Successfully Resolved!",
                message=f"Great news! Your report for '{item.title}' has been successfully resolved and reunited with its verified owner.",
                notification_type=Notification.NotificationType.ITEM_RESOLVED,
                target_url=f"/items/{item.id}/",
            )

        logger.info(f"Claim #{claim.id} APPROVED by {reviewer.username}. Item {item.id} RESOLVED.")
        return claim


def reject_claim(claim: Claim, reviewer, rejection_reason: str, admin_notes: str = "") -> Claim:
    """Atomically reject claim, store reason, and revert item to OPEN if no active claims remain."""
    if not rejection_reason or not rejection_reason.strip():
        raise ValidationError("A rejection reason must be specified when rejecting a claim.")

    with transaction.atomic():
        item = Item.objects.select_for_update().get(id=claim.item_id)
        now = timezone.now()

        claim.status = ClaimStatus.REJECTED
        claim.reviewed_by = reviewer
        claim.resolved_at = now
        claim.rejection_reason = rejection_reason.strip()
        if admin_notes:
            claim.admin_notes = admin_notes
        claim.save(update_fields=["status", "reviewed_by", "resolved_at", "rejection_reason", "admin_notes", "updated_at"])

        # Update associated match if applicable
        if claim.potential_match and claim.potential_match.status == MatchStatus.CLAIMED:
            claim.potential_match.status = MatchStatus.REJECTED
            claim.potential_match.save(update_fields=["status", "updated_at"])

        # If no other active claims remain, revert item to OPEN
        has_other_active = Claim.objects.filter(
            item=item,
            status__in=[ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW],
        ).exclude(id=claim.id).exists()

        if not has_other_active and item.status == Item.ItemStatus.CLAIM_PENDING:
            item.status = Item.ItemStatus.OPEN
            item.save(update_fields=["status", "updated_at"])

        # Notify claimant
        create_notification(
            recipient=claim.claimant,
            title="Claim Decision: Rejected",
            message=f"Your claim for '{item.title}' was reviewed and not approved. Reason: {claim.rejection_reason}",
            notification_type=Notification.NotificationType.CLAIM_REJECTED,
            target_url=f"/claims/{claim.id}/",
        )

        logger.info(f"Claim #{claim.id} REJECTED by {reviewer.username}. Reason: {rejection_reason}")
        return claim


def withdraw_claim(claim: Claim, user) -> Claim:
    """Allow authorized claimant to withdraw their active claim."""
    if not claim.can_withdraw(user):
        raise ValidationError("You do not have permission to withdraw this claim or it is already closed.")

    with transaction.atomic():
        item = Item.objects.select_for_update().get(id=claim.item_id)
        claim.status = ClaimStatus.WITHDRAWN
        claim.resolved_at = timezone.now()
        claim.save(update_fields=["status", "resolved_at", "updated_at"])

        # Revert match if applicable
        if claim.potential_match and claim.potential_match.status == MatchStatus.CLAIMED:
            claim.potential_match.status = MatchStatus.INTERESTED
            claim.potential_match.save(update_fields=["status", "updated_at"])

        # Revert item if no other active claims remain
        has_other_active = Claim.objects.filter(
            item=item,
            status__in=[ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW],
        ).exclude(id=claim.id).exists()

        if not has_other_active and item.status == Item.ItemStatus.CLAIM_PENDING:
            item.status = Item.ItemStatus.OPEN
            item.save(update_fields=["status", "updated_at"])

        create_notification(
            recipient=claim.claimant,
            title="Claim Withdrawn",
            message=f"You successfully withdrew your claim for '{item.title}'.",
            notification_type=Notification.NotificationType.CLAIM_WITHDRAWN,
            target_url=f"/claims/{claim.id}/",
        )

        logger.info(f"Claim #{claim.id} WITHDRAWN by claimant {user.username}.")
        return claim

