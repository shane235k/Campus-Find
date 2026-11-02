"""Views for student registration, authentication, profile management, and admin provisioning."""
import logging
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import FormView, UpdateView

from .forms import (
    AdminProvisioningForm,
    LoginForm,
    ProfileUpdateForm,
    StudentRegistrationForm,
)
from .models import CampusUser
from .permissions import SuperAdminRequiredMixin

logger = logging.getLogger(__name__)


class StudentRegistrationView(FormView):
    """Handles new student registration."""
    template_name = "accounts/register.html"
    form_class = StudentRegistrationForm
    success_url = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        messages.success(
            self.request,
            f"Registration successful for {user.email}! Please log in with your credentials.",
        )
        logger.info("New student registered: %s (ID: %s)", user.email, user.student_id)
        return super().form_valid(form)


class UserLoginView(FormView):
    """Handles student and administrator login."""
    template_name = "accounts/login.html"
    form_class = LoginForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return self.get_success_redirect_url(request.user)
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        user = form.get_user()
        login(self.request, user)
        messages.success(self.request, f"Welcome back, {user.first_name or user.username}!")
        logger.info("User logged in: %s (Role: %s)", user.email, user.role)
        return self.get_success_redirect_url(user)

    def get_success_redirect_url(self, user):
        next_url = self.request.POST.get("next") or self.request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts={self.request.get_host()},
            require_https=self.request.is_secure(),
        ):
            return redirect(next_url)

        # Role-based dashboard redirection
        if user.role == CampusUser.Role.SUPER_ADMIN:
            return redirect("dashboard:super_admin")
        elif user.role == CampusUser.Role.ADMIN:
            return redirect("dashboard:admin")
        return redirect("dashboard:student")


class UserLogoutView(View):
    """Handles user logout via POST request."""

    def post(self, request, *args, **kwargs):
        user_email = request.user.email if request.user.is_authenticated else "Anonymous"
        logout(request)
        messages.info(request, "You have been logged out successfully.")
        logger.info("User logged out: %s", user_email)
        return redirect("home")

    def get(self, request, *args, **kwargs):
        # Redirect GET requests directly to home to discourage unsafe logout
        return redirect("home")


class ProfileView(LoginRequiredMixin, UpdateView):
    """Displays and allows safe editing of user profile."""
    model = CampusUser
    form_class = ProfileUpdateForm
    template_name = "accounts/profile.html"
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, "Your profile has been updated successfully.")
        return super().form_valid(form)


class AdminProvisioningView(SuperAdminRequiredMixin, FormView):
    """Super Admin-only portal to provision administrative accounts."""
    template_name = "accounts/create_admin.html"
    form_class = AdminProvisioningForm
    success_url = reverse_lazy("accounts:create_admin")

    def form_valid(self, form):
        admin_user = form.save()
        messages.success(
            self.request,
            f"Administrator account for {admin_user.email} provisioned successfully.",
        )
        logger.info(
            "SuperAdmin %s provisioned new Admin: %s",
            self.request.user.email,
            admin_user.email,
        )
        return super().form_valid(form)
