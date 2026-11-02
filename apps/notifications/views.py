"""Views for notifications application (Phase 0 Placeholders)."""
from django.views.generic import TemplateView


class NotificationsIndexView(TemplateView):
    """Placeholder view for notifications interface."""
    template_name = "notifications/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Campus Notifications",
            "section_name": "Notification Center",
            "phase": "Phase 5",
            "description": "Real-time match alerts, claim status updates, and administrative broadcasts will be delivered in Phase 5.",
        })
        return context
