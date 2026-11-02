"""URL routing configuration for matching app."""
from django.urls import path
from . import views

app_name = "matching"

urlpatterns = [
    path("", views.MatchingHubView.as_view(), name="hub"),
    path("index/", views.MatchingHubView.as_view(), name="index"),
    path("item/<uuid:item_id>/", views.ItemMatchesView.as_view(), name="item_matches"),
    path("<uuid:match_id>/", views.MatchDetailView.as_view(), name="match_detail"),
    path("<uuid:match_id>/action/", views.MatchActionView.as_view(), name="match_action"),
    path("trigger/", views.TriggerMatchingView.as_view(), name="trigger_all"),
    path("item/<uuid:item_id>/trigger/", views.TriggerMatchingView.as_view(), name="trigger_item"),
]
