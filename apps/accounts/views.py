"""Views for accounts application (Phase 0 Placeholders)."""
from django.views.generic import TemplateView


class AccountsIndexView(TemplateView):
    """Placeholder view for accounts index."""
    template_name = "accounts/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Account Management",
            "section_name": "Accounts & Authentication",
            "phase": "Phase 1",
            "description": "User authentication, student registration with campus email verification, and profile management will be implemented here in Phase 1.",
        })
        return context


class LoginPlaceholderView(TemplateView):
    """Placeholder view for user login."""
    template_name = "accounts/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Student & Admin Login",
            "section_name": "Authentication — Sign In",
            "phase": "Phase 1",
            "description": "Secure sign-in with university credentials and session management will be active in Phase 1.",
        })
        return context


class RegisterPlaceholderView(TemplateView):
    """Placeholder view for user registration."""
    template_name = "accounts/placeholder.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Register Campus Account",
            "section_name": "Authentication — Sign Up",
            "phase": "Phase 1",
            "description": "Campus student registration with roll number, department, and university email verification will be active in Phase 1.",
        })
        return context
