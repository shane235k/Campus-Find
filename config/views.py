"""Root application views for Campus Lost & Found Hub."""
from django.views.generic import TemplateView


class HomeView(TemplateView):
    """Public landing page view."""
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Empty state for recently reported items in Phase 0
        context["recent_items"] = []
        context["platform_name"] = "Campus Lost & Found Hub"
        context["phase_tag"] = "Phase 0 — Foundation"
        return context
