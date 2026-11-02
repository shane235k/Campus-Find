"""URL patterns for items app."""
from django.urls import path
from . import views

app_name = "items"

urlpatterns = [
    path("", views.ItemsIndexView.as_view(), name="index"),
    path("report-lost/", views.ReportLostPlaceholderView.as_view(), name="report_lost"),
    path("report-found/", views.ReportFoundPlaceholderView.as_view(), name="report_found"),
]
