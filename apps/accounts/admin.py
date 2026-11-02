"""Admin configuration for accounts app."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CampusUser


@admin.register(CampusUser)
class CampusUserAdmin(UserAdmin):
    """Admin console configuration for CampusUser."""
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "student_id",
        "is_email_verified",
        "is_staff",
    )
    list_filter = ("role", "is_email_verified", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name", "student_id")
    ordering = ("-date_joined",)

    fieldsets = UserAdmin.fieldsets + (
        (
            "Campus Lost & Found Metadata",
            {
                "fields": (
                    "role",
                    "student_id",
                    "phone_number",
                    "profile_picture",
                    "is_email_verified",
                )
            },
        ),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Campus Lost & Found Metadata",
            {
                "fields": (
                    "email",
                    "role",
                    "student_id",
                    "phone_number",
                    "profile_picture",
                    "is_email_verified",
                )
            },
        ),
    )
