"""REST API views for items, categories, and locations."""
from django.db import transaction
from django.db.models import Q
from rest_framework import generics, permissions
from rest_framework.response import Response

from .models import CampusLocation, Category, Item
from .permissions import IsOwnerOrAdmin
from .serializers import (
    CampusLocationSerializer,
    CategorySerializer,
    ItemSerializer,
)


class CategoryListAPIView(generics.ListAPIView):
    """List active categories."""

    queryset = Category.objects.filter(is_active=True).order_by("name")
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class CampusLocationListAPIView(generics.ListAPIView):
    """List active campus locations."""

    queryset = CampusLocation.objects.filter(is_active=True).order_by("name")
    serializer_class = CampusLocationSerializer
    permission_classes = [permissions.AllowAny]


class ItemListCreateAPIView(generics.ListCreateAPIView):
    """List items with filtering and search, or create a new item report."""

    serializer_class = ItemSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = Item.objects.select_related("category", "location", "reported_by").all()
        user = self.request.user

        query = self.request.query_params.get("q", "").strip()
        item_type = self.request.query_params.get("type", "").strip().upper()
        category_id = self.request.query_params.get("category", "").strip()
        location_id = self.request.query_params.get("location", "").strip()
        status = self.request.query_params.get("status", "").strip().upper()

        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )

        if item_type in [Item.ItemType.LOST, Item.ItemType.FOUND]:
            queryset = queryset.filter(item_type=item_type)

        if category_id:
            if category_id.isdigit():
                queryset = queryset.filter(category_id=int(category_id))
            else:
                queryset = queryset.filter(category__name__iexact=category_id)

        if location_id:
            if location_id.isdigit():
                queryset = queryset.filter(location_id=int(location_id))
            else:
                queryset = queryset.filter(location__name__iexact=location_id)

        date_from = self.request.query_params.get("date_from", "").strip() or self.request.query_params.get("start_date", "").strip()
        date_to = self.request.query_params.get("date_to", "").strip() or self.request.query_params.get("end_date", "").strip()
        if date_from:
            queryset = queryset.filter(date_lost_or_found__gte=date_from)
        if date_to:
            queryset = queryset.filter(date_lost_or_found__lte=date_to)

        if status in [s[0] for s in Item.ItemStatus.choices]:
            queryset = queryset.filter(status=status)
        else:
            is_admin = user.is_authenticated and getattr(user, "is_admin_user", False)
            if not is_admin:
                queryset = queryset.filter(
                    status__in=[Item.ItemStatus.OPEN, Item.ItemStatus.CLAIM_PENDING]
                )

        return queryset.order_by("-created_at")


class ItemRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete an item report."""

    queryset = Item.objects.select_related("category", "location", "reported_by")
    serializer_class = ItemSerializer
    permission_classes = [IsOwnerOrAdmin]

    def perform_destroy(self, instance):
        image = instance.image
        with transaction.atomic():
            super().perform_destroy(instance)
        if image:
            try:
                image.delete(save=False)
            except Exception:
                pass

