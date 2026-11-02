"""AppConfig for matching app."""
from django.apps import AppConfig


class MatchingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.matching"
    verbose_name = "AI Semantic Matching"

    def ready(self):
        import apps.matching.signals  # noqa: F401
