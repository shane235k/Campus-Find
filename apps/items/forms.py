"""Forms for reporting, editing, and managing lost and found items."""
import logging
from datetime import date
from django import forms
from django.core.exceptions import ValidationError
from django.db import models

from .models import CampusLocation, Category, Item
from .utils import validate_item_image

logger = logging.getLogger(__name__)


class ItemReportForm(forms.ModelForm):
    """Reusable base form for reporting lost and found belongings."""

    title = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g., Black Dell XPS 15 with GitHub Sticker",
                "autofocus": True,
            }
        ),
        help_text="Give a clear, recognizable title identifying the item.",
    )

    description = forms.CharField(
        required=True,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe physical appearance, brand, distinctive stickers, case color, scratches, or contents...",
            }
        ),
        help_text="Provide specific distinguishing details to help identify the item.",
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.none(),
        required=True,
        empty_label="Select Classification Category",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Choose the category that best matches your item.",
    )

    location = forms.ModelChoiceField(
        queryset=CampusLocation.objects.none(),
        required=True,
        empty_label="Select Campus Location",
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Where on campus was this item lost or discovered?",
    )

    date_lost_or_found = forms.DateField(
        required=True,
        widget=forms.DateInput(
            attrs={
                "class": "form-control",
                "type": "date",
            }
        ),
        help_text="Date when the incident occurred.",
    )

    image = forms.ImageField(
        required=False,
        validators=[validate_item_image],
        widget=forms.FileInput(
            attrs={
                "class": "form-control",
                "accept": "image/jpeg,image/png,image/webp",
            }
        ),
        help_text="Optional photograph (max 5 MB; JPG, PNG, WEBP).",
    )

    class Meta:
        model = Item
        fields = ("title", "description", "category", "location", "date_lost_or_found", "image")

    def __init__(self, *args, **kwargs):
        self.item_type = kwargs.pop("item_type", None)
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # Restrict querysets strictly to active categories and locations
        self.fields["category"].queryset = Category.objects.filter(is_active=True).order_by("name")
        self.fields["location"].queryset = CampusLocation.objects.filter(is_active=True).order_by("name")

        # Set max date attribute to today to prevent selecting future dates
        today_str = date.today().isoformat()
        self.fields["date_lost_or_found"].widget.attrs["max"] = today_str

        # Adapt labels according to item_type
        if self.item_type == Item.ItemType.LOST:
            self.fields["date_lost_or_found"].label = "Date Lost"
            self.fields["location"].label = "Location Lost"
        elif self.item_type == Item.ItemType.FOUND:
            self.fields["date_lost_or_found"].label = "Date Found"
            self.fields["location"].label = "Location Discovered"

    def clean_category(self):
        category = self.cleaned_data.get("category")
        if category and not category.is_active:
            raise ValidationError("The selected category is inactive. Please choose an active category.")
        return category

    def clean_location(self):
        location = self.cleaned_data.get("location")
        if location and not location.is_active:
            raise ValidationError("The selected campus location is inactive. Please choose an active location.")
        return location

    def clean_date_lost_or_found(self):
        incident_date = self.cleaned_data.get("date_lost_or_found")
        if incident_date and incident_date > date.today():
            raise ValidationError("The lost/found date cannot be in the future.")
        return incident_date

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.user:
            instance.reported_by = self.user
        if self.item_type:
            instance.item_type = self.item_type
        # Newly created reports always receive OPEN status automatically
        if not instance.pk:
            instance.status = Item.ItemStatus.OPEN
        if commit:
            instance.save()
        return instance


class ItemEditForm(forms.ModelForm):
    """Editing form for existing reports.
    
    Prevents changing the reporting student, the report type, or the operational status.
    Allows replacing or explicitly removing an existing image while preserving it on error.
    """

    remove_image = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
        label="Remove current photograph",
        help_text="Check this box to delete the existing image without uploading a replacement.",
    )

    class Meta:
        model = Item
        fields = ("title", "description", "category", "location", "date_lost_or_found", "image")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "location": forms.Select(attrs={"class": "form-select"}),
            "date_lost_or_found": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "image": forms.FileInput(attrs={"class": "form-control", "accept": "image/jpeg,image/png,image/webp"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initial_image_name = (
            self.instance.image.name if (self.instance and self.instance.pk and self.instance.image) else None
        )

        # Category/location querysets: active plus the currently assigned one to allow editing legacy items
        current_cat_id = self.instance.category_id if self.instance.pk else None
        current_loc_id = self.instance.location_id if self.instance.pk else None

        self.fields["category"].queryset = Category.objects.filter(
            models.Q(is_active=True) | models.Q(id=current_cat_id)
        ).order_by("name")
        self.fields["location"].queryset = CampusLocation.objects.filter(
            models.Q(is_active=True) | models.Q(id=current_loc_id)
        ).order_by("name")

        today_str = date.today().isoformat()
        self.fields["date_lost_or_found"].widget.attrs["max"] = today_str

        # Hide remove_image checkbox if item doesn't have an image
        if not self.instance.image:
            self.fields.pop("remove_image", None)

    def clean_date_lost_or_found(self):
        incident_date = self.cleaned_data.get("date_lost_or_found")
        if incident_date and incident_date > date.today():
            raise ValidationError("The lost/found date cannot be in the future.")
        return incident_date

    def save(self, commit=True):
        instance = super().save(commit=False)
        remove_image = self.cleaned_data.get("remove_image", False)
        new_file_uploaded = bool(self.files and self.files.get("image"))

        if remove_image:
            if instance.image:
                try:
                    instance.image.close()
                except Exception:
                    pass
            if self._initial_image_name:
                import gc
                gc.collect()
                try:
                    instance.image.storage.delete(self._initial_image_name)
                except Exception as exc:
                    logger.warning("Error deleting removed image: %s", exc)
            instance.image = None
        elif new_file_uploaded and self._initial_image_name:
            import gc
            gc.collect()
            try:
                instance.image.storage.delete(self._initial_image_name)
            except Exception as exc:
                logger.warning("Error deleting replaced image: %s", exc)

        if commit:
            instance.save()
        return instance


class ItemStatusUpdateForm(forms.ModelForm):
    """Admin-only status moderation form."""

    status = forms.ChoiceField(
        choices=Item.ItemStatus.choices,
        widget=forms.Select(attrs={"class": "form-select"}),
        help_text="Update the operational status of this report.",
    )

    class Meta:
        model = Item
        fields = ("status",)
