"""Django REST Framework serializers for items, categories, and campus locations."""
from datetime import date
from rest_framework import serializers

from .models import CampusLocation, Category, Item
from .utils import MAX_IMAGE_SIZE_BYTES, validate_item_image


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "description", "is_active")


class CampusLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampusLocation
        fields = ("id", "name", "description", "is_active")


class ItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    location_name = serializers.CharField(source="location.name", read_only=True)
    reporter_display_name = serializers.CharField(read_only=True)

    class Meta:
        model = Item
        fields = (
            "id",
            "title",
            "description",
            "item_type",
            "category",
            "category_name",
            "location",
            "location_name",
            "date_lost_or_found",
            "image",
            "status",
            "reporter_display_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "status", "reporter_display_name", "created_at", "updated_at")

    def validate_category(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Selected category is inactive.")
        return value

    def validate_location(self, value):
        if not value.is_active:
            raise serializers.ValidationError("Selected campus location is inactive.")
        return value

    def validate_date_lost_or_found(self, value):
        if value > date.today():
            raise serializers.ValidationError("Incident date cannot be in the future.")
        return value

    def validate_image(self, value):
        if value:
            validate_item_image(value)
        return value

    def create(self, validated_data):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        validated_data["reported_by"] = user
        validated_data["status"] = Item.ItemStatus.OPEN
        return super().create(validated_data)
