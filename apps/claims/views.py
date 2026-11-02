"""Views for claims application (Phase 0 Placeholders)."""
from django.views.generic import TemplateView


class ClaimsIndexView(TemplateView):
    """Placeholder view for claims interface."""
    template_name = "claims/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Ownership Claims & Verification",
            "section_name": "Claims Center",
            "phase": "Phase 4",
            "description": "Submit proof of ownership, upload purchase receipts or identifying marks, and track administrative claim reviews in Phase 4.",
        })
        return context
