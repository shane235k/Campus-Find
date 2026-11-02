"""DRF permissions for items application."""
from rest_framework import permissions


class IsOwnerOrAdmin(permissions.BasePermission):
    """Object-level permission allowing only the owner or an admin to modify/delete an item."""

    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request
        if request.method in permissions.SAFE_METHODS:
            return True

        if not request.user or not request.user.is_authenticated:
            return False

        is_owner = obj.reported_by_id == request.user.pk
        is_admin = getattr(request.user, "is_admin_user", False)
        return is_owner or is_admin
