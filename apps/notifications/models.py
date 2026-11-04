"""Database models for notifications application."""
import uuid
from django.conf import settings
from django.db import models


class Notification(models.Model):
    """In-app user notification for match alerts, claim lifecycle, and system updates."""

    class NotificationType(models.TextChoices):
        CLAIM_SUBMITTED = "CLAIM_SUBMITTED", "Claim Submitted"
        CLAIM_UNDER_REVIEW = "CLAIM_UNDER_REVIEW", "Claim Under Review"
        CLAIM_APPROVED = "CLAIM_APPROVED", "Claim Approved"
        CLAIM_REJECTED = "CLAIM_REJECTED", "Claim Rejected"
        CLAIM_WITHDRAWN = "CLAIM_WITHDRAWN", "Claim Withdrawn"
        ITEM_RESOLVED = "ITEM_RESOLVED", "Item Resolved"
        MATCH_FOUND = "MATCH_FOUND", "Match Discovered"
        SYSTEM = "SYSTEM", "System Notification"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="User receiving the notification.",
    )
    title = models.CharField(max_length=150, help_text="Notification heading.")
    message = models.TextField(help_text="Detailed notification content.")
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        db_index=True,
    )
    target_url = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Optional destination URL when notification is clicked.",
    )
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.notification_type}] {self.title} -> {self.recipient.username}"

    def mark_as_read(self):
        """Marks this notification as read."""
        if not self.is_read:
            self.is_read = True
            self.save(update_fields=["is_read"])


NotificationType = Notification.NotificationType


def create_notification(
    recipient,
    title: str,
    message: str,
    notification_type: str = Notification.NotificationType.SYSTEM,
    target_url: str = "",
) -> Notification:
    """Helper function to create and persist an in-app notification."""
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        target_url=target_url,
    )
