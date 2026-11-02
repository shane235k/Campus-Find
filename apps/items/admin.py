"""Admin configuration for items app: Category, CampusLocation, and Item."""
from django.contrib import admin
from .models import CampusLocation, Category, Item


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(CampusLocation)
class CampusLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    ordering = ("name",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "item_type",
        "category",
        "location",
        "status",
        "date_lost_or_found",
        "reported_by",
        "created_at",
    )
    list_filter = (
        "item_type",
        "status",
        "category",
        "location",
        "date_lost_or_found",
    )
    search_fields = (
        "title",
        "description",
        "reported_by__email",
        "reported_by__username",
        "reported_by__student_id",
    )
    readonly_fields = ("id", "created_at", "updated_at")
    raw_id_fields = ("reported_by",)
    fieldsets = (
        (
            "Report Classification",
            {
                "fields": ("id", "item_type", "title", "description", "category", "location"),
            },
        ),
        (
            "Timeline & Evidence",
            {
                "fields": ("date_lost_or_found", "image"),
            },
        ),
        (
            "Governance & Ownership",
            {
                "fields": ("reported_by", "status", "created_at", "updated_at"),
            },
        ),
    )
