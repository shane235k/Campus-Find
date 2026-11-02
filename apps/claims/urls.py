"""URL patterns for claims app."""
from django.urls import path
from . import views

app_name = "claims"

urlpatterns = [
    path("", views.ClaimsIndexView.as_view(), name="index"),
]
