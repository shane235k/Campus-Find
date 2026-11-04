"""URL configuration for claims application."""
from django.urls import path
from . import views

app_name = "claims"

urlpatterns = [
    path("", views.StudentClaimsListView.as_view(), name="index"),
    path("my-claims/", views.StudentClaimsListView.as_view(), name="my_claims"),
    path("submit/<uuid:item_id>/", views.ClaimSubmissionView.as_view(), name="submit"),
    path("<uuid:claim_id>/", views.ClaimDetailView.as_view(), name="detail"),
    path("<uuid:claim_id>/withdraw/", views.ClaimWithdrawView.as_view(), name="withdraw"),
    path("admin/", views.AdminClaimsDashboardView.as_view(), name="admin_dashboard"),
    path("admin/<uuid:claim_id>/", views.AdminClaimReviewView.as_view(), name="admin_review"),
]
