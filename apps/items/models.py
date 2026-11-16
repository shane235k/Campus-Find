"""Models for items application: Category, CampusLocation, and Item."""
import uuid
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .utils import item_image_upload_path, validate_item_image


class Category(models.Model):
    """Categorical classification for lost and found items (e.g., Electronics, IDs, Books)."""

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique name of the category.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional description or examples of belongings in this category.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Controls whether this category is selectable for new reports.",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        help_text="Timestamp when the category was created.",
    )

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class CampusLocation(models.Model):
    """University campus physical locations and designated lost & found recovery points."""

    name = models.CharField(
        max_length=120,
        unique=True,
        help_text="Campus building, facility, or landmark name.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional details such as floor, room numbers, or nearby landmarks.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Controls whether this campus location is selectable for new reports.",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        help_text="Timestamp when the location was registered.",
    )

    class Meta:
        verbose_name = "Campus Location"
        verbose_name_plural = "Campus Locations"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Item(models.Model):
    """Core Lost & Found item report."""

    class ItemType(models.TextChoices):
        LOST = "LOST", "Lost"
        FOUND = "FOUND", "Found"

    class ItemStatus(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLAIM_PENDING = "CLAIM_PENDING", "Claim Pending"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    # Explicit allowed operational status transitions
    VALID_STATUS_TRANSITIONS = {
        "OPEN": {"OPEN", "CLAIM_PENDING", "RESOLVED", "CLOSED"},
        "CLAIM_PENDING": {"CLAIM_PENDING", "OPEN", "RESOLVED", "CLOSED"},
        "RESOLVED": {"RESOLVED", "OPEN", "CLOSED"},
        "CLOSED": {"CLOSED", "OPEN"},
    }

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique item report identifier.",
    )
    title = models.CharField(
        max_length=200,
        help_text="Brief headline identifying the item.",
    )
    description = models.TextField(
        help_text="Detailed narrative describing physical appearance, brand, colors, and identifiers.",
    )
    item_type = models.CharField(
        max_length=10,
        choices=ItemType.choices,
        help_text="Indicates whether this report is for a LOST or FOUND item.",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="items",
        help_text="Classification category of the item.",
    )
    location = models.ForeignKey(
        CampusLocation,
        on_delete=models.PROTECT,
        related_name="items",
        help_text="Campus location where the item was lost or found.",
    )
    date_lost_or_found = models.DateField(
        help_text="Date when the item was lost or discovered.",
    )
    image = models.ImageField(
        upload_to=item_image_upload_path,
        blank=True,
        null=True,
        max_length=255,
        validators=[validate_item_image],
        help_text="Optional photograph of the item (max 5 MB; JPG, PNG, WEBP).",
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reported_items",
        help_text="Campus student who filed this report.",
    )
    status = models.CharField(
        max_length=20,
        choices=ItemStatus.choices,
        default=ItemStatus.OPEN,
        help_text="Current operational status of this lost & found report.",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        help_text="Timestamp when this report was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when this report was last modified.",
    )

    class Meta:
        verbose_name = "Item"
        verbose_name_plural = "Items"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["item_type", "status"]),
            models.Index(fields=["date_lost_or_found"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.get_item_type_display()}: {self.title} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse("items:detail", kwargs={"pk": self.pk})

    def can_transition_to(self, new_status):
        """Check whether transition from current status to new_status is allowed."""
        allowed = self.VALID_STATUS_TRANSITIONS.get(self.status, {self.status})
        return new_status in allowed

    @property
    def is_lost(self):
        return self.item_type == self.ItemType.LOST

    @property
    def is_found(self):
        return self.item_type == self.ItemType.FOUND

    @property
    def is_open(self):
        return self.status == self.ItemStatus.OPEN

    @property
    def is_claim_pending(self):
        return self.status == self.ItemStatus.CLAIM_PENDING

    @property
    def is_resolved(self):
        return self.status == self.ItemStatus.RESOLVED

    @property
    def is_closed(self):
        return self.status == self.ItemStatus.CLOSED

    @property
    def reporter_display_name(self):
        """Returns safe public display name of the reporting user.
        
        Strictly prevents leaking email, phone number, or student ID.
        """
        full_name = self.reported_by.get_full_name().strip()
        if full_name:
            return full_name
        return self.reported_by.username


class StoredImage(models.Model):
    """Stores persistent image binary data in the database so images survive across multiple devices."""

    filename = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Filename of the stored image (e.g. watch_found.png).",
    )
    content_type = models.CharField(
        max_length=50,
        default="image/png",
        help_text="MIME type of the image (e.g. image/png, image/jpeg).",
    )
    image_base64 = models.TextField(
        help_text="Base64-encoded image data stored in the database.",
    )
    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
    )

    class Meta:
        verbose_name = "Stored Image"
        verbose_name_plural = "Stored Images"
        ordering = ["filename"]

    def __str__(self):
        return self.filename

