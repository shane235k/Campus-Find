"""URL patterns for matching app."""
from django.urls import path
from . import views

app_name = "matching"

urlpatterns = [
    path("", views.MatchingIndexView.as_view(), name="index"),
]
