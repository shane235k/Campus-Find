"""Role-based access control decorators and mixins."""
from functools import wraps
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from .models import CampusUser


def role_required(*allowed_roles):
    """Decorator for views that checks whether a user has one of the allowed roles.
    
    If unauthenticated, redirects to login.
    If authenticated without role, raises PermissionDenied (HTTP 403).
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("accounts:login")
            if request.user.role not in allowed_roles:
                raise PermissionDenied("You do not have permission to access this resource.")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def student_required(view_func):
    """Restricts view to authenticated students."""
    return role_required(CampusUser.Role.STUDENT)(view_func)


def admin_required(view_func):
    """Restricts view to administrators and super administrators."""
    return role_required(CampusUser.Role.ADMIN, CampusUser.Role.SUPER_ADMIN)(view_func)


def super_admin_required(view_func):
    """Restricts view exclusively to super administrators."""
    return role_required(CampusUser.Role.SUPER_ADMIN)(view_func)


class RoleRequiredMixin(AccessMixin):
    """CBV Mixin to enforce required application roles."""
    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.allowed_roles and request.user.role not in self.allowed_roles:
            raise PermissionDenied("You do not have permission to access this resource.")
        return super().dispatch(request, *args, **kwargs)


class StudentRequiredMixin(RoleRequiredMixin):
    allowed_roles = (CampusUser.Role.STUDENT,)


class AdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (CampusUser.Role.ADMIN, CampusUser.Role.SUPER_ADMIN)


class SuperAdminRequiredMixin(RoleRequiredMixin):
    allowed_roles = (CampusUser.Role.SUPER_ADMIN,)
