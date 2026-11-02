"""Views for items application (Phase 0 Placeholders)."""
from django.views.generic import TemplateView


class ItemsIndexView(TemplateView):
    """Placeholder view for items listing."""
    template_name = "items/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Campus Items Directory",
            "section_name": "Lost & Found Items Directory",
            "phase": "Phase 2",
            "description": "Browse, filter, and search campus lost and found items. Item listings, category filtering, campus location tags, and image galleries will be implemented in Phase 2.",
        })
        return context


class ReportLostPlaceholderView(TemplateView):
    """Placeholder view for reporting a lost item."""
    template_name = "items/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Report Lost Item",
            "section_name": "Report Lost Item",
            "phase": "Phase 2",
            "description": "Multi-step form for reporting lost belongings, uploading photos, specifying campus locations, and configuring match alerts will be active in Phase 2.",
        })
        return context


class ReportFoundPlaceholderView(TemplateView):
    """Placeholder view for reporting a found item."""
    template_name = "items/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Report Found Item",
            "section_name": "Report Found Item",
            "phase": "Phase 2",
            "description": "Found item logging with handover instructions, storage locker assignments, and finder contact management will be active in Phase 2.",
        })
        return context
