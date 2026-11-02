"""Views for matching application (Phase 0 Placeholders)."""
from django.views.generic import TemplateView


class MatchingIndexView(TemplateView):
    """Placeholder view for semantic matching interface."""
    template_name = "matching/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "AI Semantic Matching Engine",
            "section_name": "Semantic Matching Hub",
            "phase": "Phase 3",
            "description": "Sentence Transformers (all-MiniLM-L6-v2) combined with PostgreSQL pgvector cosine similarity ranking will dynamically identify matching lost and found items in Phase 3.",
        })
        return context
