"""Views for student, admin, and super-admin dashboards."""
from django.shortcuts import redirect
from django.views.generic import TemplateView
from apps.accounts.models import CampusUser
from apps.accounts.permissions import (
    AdminRequiredMixin,
    StudentRequiredMixin,
    SuperAdminRequiredMixin,
)


class DashboardDispatcher(TemplateView):
    """Dispatches authenticated users to their designated role dashboard."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if request.user.role == CampusUser.Role.SUPER_ADMIN:
            return redirect("dashboard:super_admin")
        elif request.user.role == CampusUser.Role.ADMIN:
            return redirect("dashboard:admin")
        return redirect("dashboard:student")


class StudentDashboardView(StudentRequiredMixin, TemplateView):
    """Student activity portal (my reported items, claims, notifications)."""
    template_name = "dashboard/student.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Student Dashboard",
            "active_tab": "dashboard",
        })
        return context


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """Administrator moderation console."""
    template_name = "dashboard/admin.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Administrator Operations Console",
            "active_tab": "admin_dashboard",
        })
        return context


class SuperAdminDashboardView(SuperAdminRequiredMixin, TemplateView):
    """Super Administrator command center."""
    template_name = "dashboard/super_admin.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Super Administrator Command Center",
            "active_tab": "super_admin_dashboard",
            "total_users": CampusUser.objects.count(),
            "student_count": CampusUser.objects.filter(role=CampusUser.Role.STUDENT).count(),
            "admin_count": CampusUser.objects.filter(role=CampusUser.Role.ADMIN).count(),
        })
        return context
