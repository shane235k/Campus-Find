"""URL routes for notifications application."""
from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("", views.NotificationListView.as_view(), name="list"),
    path("", views.NotificationListView.as_view(), name="index"),
    path("<uuid:pk>/read/", views.MarkNotificationReadView.as_view(), name="mark_read"),
    path("mark-all-read/", views.MarkAllNotificationsReadView.as_view(), name="mark_all_read"),
]
