"""URL patterns for accounts app."""
from django.shortcuts import redirect
from django.urls import path
from . import views

app_name = "accounts"


def accounts_index_redirect(request):
    if request.user.is_authenticated:
        return redirect("accounts:profile")
    return redirect("accounts:login")


urlpatterns = [
    path("", accounts_index_redirect, name="index"),
    path("register/", views.StudentRegistrationView.as_view(), name="register"),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("admin/provision/", views.AdminProvisioningView.as_view(), name="create_admin"),
]
