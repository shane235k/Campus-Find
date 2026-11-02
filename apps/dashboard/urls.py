"""URL patterns for dashboard app."""
from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.DashboardDispatcher.as_view(), name="index"),
    path("student/", views.StudentDashboardView.as_view(), name="student"),
    path("admin/", views.AdminDashboardView.as_view(), name="admin"),
    path("super-admin/", views.SuperAdminDashboardView.as_view(), name="super_admin"),
]
