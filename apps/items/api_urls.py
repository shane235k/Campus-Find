"""API URL patterns for items, categories, and locations."""
from django.urls import path
from . import api_views

app_name = "items_api"

urlpatterns = [
    path("items/", api_views.ItemListCreateAPIView.as_view(), name="item_list_create"),
    path("items/", api_views.ItemListCreateAPIView.as_view(), name="item-list"),
    path("items/<uuid:pk>/", api_views.ItemRetrieveUpdateDestroyAPIView.as_view(), name="item_detail"),
    path("items/<uuid:pk>/", api_views.ItemRetrieveUpdateDestroyAPIView.as_view(), name="item-detail"),
    path("categories/", api_views.CategoryListAPIView.as_view(), name="category_list"),
    path("categories/", api_views.CategoryListAPIView.as_view(), name="category-list"),
    path("locations/", api_views.CampusLocationListAPIView.as_view(), name="location_list"),
    path("locations/", api_views.CampusLocationListAPIView.as_view(), name="location-list"),
]
