"""Django admin registration for claims."""
from django.contrib import admin
from .models import Claim


@admin.register(Claim)
class ClaimAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "claimant",
        "item",
        "status",
        "reviewed_by",
        "created_at",
        "resolved_at",
    )
    list_filter = ("status", "created_at", "resolved_at")
    search_fields = (
        "claimant__username",
        "claimant__email",
        "item__title",
        "claim_description",
        "distinguishing_features",
        "rejection_reason",
    )
    readonly_fields = ("id", "created_at", "updated_at", "resolved_at")
    fieldsets = (
        (
            "Claim Core",
            {
                "fields": (
                    "id",
                    "claimant",
                    "item",
                    "potential_match",
                    "status",
                )
            },
        ),
        (
            "Confidential Evidence (Private)",
            {
                "fields": (
                    "claim_description",
                    "distinguishing_features",
                    "item_contents",
                    "last_seen_details",
                    "evidence_file",
                )
            },
        ),
        (
            "Review & Decision",
            {
                "fields": (
                    "reviewed_by",
                    "admin_notes",
                    "rejection_reason",
                    "resolved_at",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
