"""Database models for AI Semantic Matching Engine."""
import uuid
from django.db import models
from django.core.exceptions import ValidationError
from pgvector.django import VectorField


class MatchStatus(models.TextChoices):
    SUGGESTED = "SUGGESTED", "Suggested Match"
    INTERESTED = "INTERESTED", "Interested"
    DISMISSED = "DISMISSED", "Dismissed"
    CLAIMED = "CLAIMED", "Claim Initiated"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"


class ItemEmbedding(models.Model):
    """Stores dense 384-dimensional semantic embedding for an Item."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.OneToOneField(
        "items.Item",
        on_delete=models.CASCADE,
        related_name="embedding",
        help_text="Associated lost or found item report.",
    )
    embedding = VectorField(dimensions=384, help_text="384-dimensional dense text embedding.")
    model_name = models.CharField(max_length=100, default="all-MiniLM-L6-v2")
    text_hash = models.CharField(max_length=64, blank=True, help_text="SHA-256 hash of serialized text.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Item Embedding"
        verbose_name_plural = "Item Embeddings"

    def __str__(self):
        return f"Embedding for [{self.item.item_type}] {self.item.title} ({self.model_name})"


class PotentialMatch(models.Model):
    """Represents an intelligent candidate match between a LOST item and a FOUND item."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lost_item = models.ForeignKey(
        "items.Item",
        on_delete=models.CASCADE,
        related_name="lost_matches",
        help_text="The lost item report.",
    )
    found_item = models.ForeignKey(
        "items.Item",
        on_delete=models.CASCADE,
        related_name="found_matches",
        help_text="The found item report.",
    )
    description_similarity = models.FloatField(default=0.0, help_text="Semantic description similarity (0.0 to 1.0).")
    title_similarity = models.FloatField(default=0.0, help_text="Title text similarity (0.0 to 1.0).")
    category_score = models.FloatField(default=0.0, help_text="Category match score (0.0 to 1.0).")
    location_score = models.FloatField(default=0.0, help_text="Location proximity score (0.0 to 1.0).")
    date_score = models.FloatField(default=0.0, help_text="Date proximity decay score (0.0 to 1.0).")
    final_score = models.FloatField(default=0.0, help_text="Weighted composite match score (0.0 to 1.0).")
    status = models.CharField(
        max_length=20,
        choices=MatchStatus.choices,
        default=MatchStatus.SUGGESTED,
        db_index=True,
    )
    explanation = models.TextField(blank=True, help_text="Human-readable explanation of match reasoning.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Potential Match"
        verbose_name_plural = "Potential Matches"
        ordering = ["-final_score", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["lost_item", "found_item"],
                name="unique_lost_found_match_pair",
            )
        ]

    def clean(self):
        super().clean()
        if self.lost_item_id and self.lost_item.item_type != "LOST":
            raise ValidationError({"lost_item": "lost_item must have item_type 'LOST'."})
        if self.found_item_id and self.found_item.item_type != "FOUND":
            raise ValidationError({"found_item": "found_item must have item_type 'FOUND'."})
        if self.lost_item_id and self.found_item_id and self.lost_item_id == self.found_item_id:
            raise ValidationError("An item cannot be matched with itself.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Match: [{self.lost_item.title}] <-> [{self.found_item.title}] ({self.match_percentage}%)"

    @property
    def match_percentage(self) -> int:
        return int(round(self.final_score * 100))

    @property
    def is_strong_match(self) -> bool:
        return self.final_score >= 0.70

    @property
    def is_moderate_match(self) -> bool:
        return 0.45 <= self.final_score < 0.70
