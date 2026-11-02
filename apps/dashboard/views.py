"""Views for dashboard application (Phase 0 Placeholders)."""
from django.views.generic import TemplateView


class DashboardIndexView(TemplateView):
    """Placeholder view for student and admin dashboard."""
    template_name = "dashboard/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Campus Dashboard",
            "section_name": "Analytics & Control Center",
            "phase": "Phase 5",
            "description": "Student activity tracking (reported items, active claims) and administrative metrics (recovery rate, unresolved claims, audit logs) will be available in Phase 5.",
        })
        return context
