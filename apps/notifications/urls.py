"""URL patterns for notifications app."""
from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationsIndexView.as_view(), name="index"),
]
