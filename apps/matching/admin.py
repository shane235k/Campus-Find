"""Django admin configuration for matching models."""
from django.contrib import admin
from .models import ItemEmbedding, PotentialMatch


@admin.register(ItemEmbedding)
class ItemEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("item", "model_name", "created_at", "updated_at")
    search_fields = ("item__title", "model_name", "text_hash")
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(PotentialMatch)
class PotentialMatchAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "lost_item",
        "found_item",
        "final_score",
        "status",
        "category_score",
        "location_score",
        "date_score",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("lost_item__title", "found_item__title", "explanation")
    readonly_fields = (
        "id",
        "description_similarity",
        "title_similarity",
        "category_score",
        "location_score",
        "date_score",
        "final_score",
        "explanation",
        "created_at",
        "updated_at",
    )
