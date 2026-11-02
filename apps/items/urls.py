"""URL patterns for items application."""
from django.shortcuts import redirect
from django.urls import path
from . import views

app_name = "items"

urlpatterns = [
    path("", views.ItemListView.as_view(), name="list"),
    path("", views.ItemListView.as_view(), name="index"),
    path("report/lost/", views.ReportLostItemView.as_view(), name="report_lost"),
    path("report/found/", views.ReportFoundItemView.as_view(), name="report_found"),
    
    # Backwards-compatible legacy shortcuts
    path("report-lost/", lambda request: redirect("items:report_lost"), name="report_lost_legacy"),
    path("report-found/", lambda request: redirect("items:report_found"), name="report_found_legacy"),

    # Item detail, editing, and deletion
    path("<uuid:pk>/", views.ItemDetailView.as_view(), name="detail"),
    path("<uuid:pk>/edit/", views.ItemUpdateView.as_view(), name="edit"),
    path("<uuid:pk>/delete/", views.ItemDeleteView.as_view(), name="delete"),
    path("<uuid:pk>/status/", views.ItemStatusUpdateView.as_view(), name="update_status"),
]
