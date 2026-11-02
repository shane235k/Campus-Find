"""URL patterns for accounts app."""
from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    path("", views.AccountsIndexView.as_view(), name="index"),
    path("login/", views.LoginPlaceholderView.as_view(), name="login"),
    path("register/", views.RegisterPlaceholderView.as_view(), name="register"),
]
