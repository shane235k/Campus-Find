"""Views for items application: listing, search, reporting, detail, editing, and deletion."""
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import DetailView, FormView, ListView, UpdateView

from apps.accounts.permissions import AdminRequiredMixin

from .forms import ItemEditForm, ItemReportForm, ItemStatusUpdateForm
from .models import CampusLocation, Category, Item

logger = logging.getLogger(__name__)


class ItemListView(ListView):
    """Filterable and paginated directory of campus lost and found reports."""

    model = Item
    template_name = "items/list.html"
    context_object_name = "items"
    paginate_by = 9

    def get_queryset(self):
        queryset = Item.objects.select_related("category", "location", "reported_by").all()
        user = self.request.user

        # Extract GET filter parameters
        query = self.request.GET.get("q", "").strip()
        item_type = self.request.GET.get("type", "").strip().upper()
        category_id = self.request.GET.get("category", "").strip()
        location_id = self.request.GET.get("location", "").strip()
        status = self.request.GET.get("status", "").strip().upper()
        date_from = self.request.GET.get("date_from", "").strip() or self.request.GET.get("start_date", "").strip()
        date_to = self.request.GET.get("date_to", "").strip() or self.request.GET.get("end_date", "").strip()

        # 1. Text Search across Title and Description
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )

        # 2. Filter by Item Type (LOST, FOUND)
        if item_type in [Item.ItemType.LOST, Item.ItemType.FOUND]:
            queryset = queryset.filter(item_type=item_type)

        # 3. Filter by Category
        if category_id:
            if category_id.isdigit():
                queryset = queryset.filter(category_id=int(category_id))
            else:
                queryset = queryset.filter(category__name__iexact=category_id)

        # 4. Filter by Location
        if location_id:
            if location_id.isdigit():
                queryset = queryset.filter(location_id=int(location_id))
            else:
                queryset = queryset.filter(location__name__iexact=location_id)

        # 5. Filter by Incident Date Range
        if date_from:
            queryset = queryset.filter(date_lost_or_found__gte=date_from)
        if date_to:
            queryset = queryset.filter(date_lost_or_found__lte=date_to)

        # 6. Status Visibility Rules:
        # If an explicit valid status filter is provided:
        if status in [s[0] for s in Item.ItemStatus.choices]:
            queryset = queryset.filter(status=status)
        else:
            # Default public visibility: RESOLVED and CLOSED reports are hidden from the default public browsing results
            # Admins or users explicitly reviewing everything can see all, but public default only shows active items.
            is_admin = user.is_authenticated and getattr(user, "is_admin_user", False)
            if not is_admin:
                queryset = queryset.filter(
                    status__in=[Item.ItemStatus.OPEN, Item.ItemStatus.CLAIM_PENDING]
                )

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Lost & Found Catalog",
            "categories": Category.objects.filter(is_active=True).order_by("name"),
            "locations": CampusLocation.objects.filter(is_active=True).order_by("name"),
            "current_query": self.request.GET.get("q", "").strip(),
            "current_type": self.request.GET.get("type", "").strip().upper(),
            "current_category": self.request.GET.get("category", "").strip(),
            "current_location": self.request.GET.get("location", "").strip(),
            "current_status": self.request.GET.get("status", "").strip().upper(),
            "current_date_from": self.request.GET.get("date_from", "").strip(),
            "current_date_to": self.request.GET.get("date_to", "").strip(),
            "total_count": self.get_queryset().count(),
        })
        return context


class ReportLostItemView(LoginRequiredMixin, FormView):
    """Report a misplaced or lost personal item."""

    template_name = "items/report.html"
    form_class = ItemReportForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["item_type"] = Item.ItemType.LOST
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Report a Lost Item",
            "item_type": Item.ItemType.LOST,
            "badge_color": "danger",
            "header_icon": "bi-search",
            "headline": "Report Misplaced Belongings",
            "subheadline": "Submit details of your missing item so campus members and staff can help identify it.",
        })
        return context

    def form_valid(self, form):
        item = form.save()
        messages.success(
            self.request,
            f"Lost item report '{item.title}' submitted successfully. Our campus desk will monitor incoming turn-ins.",
        )
        logger.info("Lost item reported: %s by %s", item.id, self.request.user.email)
        return redirect(item.get_absolute_url())


class ReportFoundItemView(LoginRequiredMixin, FormView):
    """Report an item found anywhere on campus."""

    template_name = "items/report.html"
    form_class = ItemReportForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["item_type"] = Item.ItemType.FOUND
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Report a Found Item",
            "item_type": Item.ItemType.FOUND,
            "badge_color": "success",
            "header_icon": "bi-box-seam",
            "headline": "Report Found Belongings",
            "subheadline": "Log items you discovered on campus so the rightful owner can verify and claim them.",
        })
        return context

    def form_valid(self, form):
        item = form.save()
        messages.success(
            self.request,
            f"Found item report '{item.title}' logged successfully. Thank you for helping our campus community!",
        )
        logger.info("Found item reported: %s by %s", item.id, self.request.user.email)
        return redirect(item.get_absolute_url())


class ItemDetailView(DetailView):
    """Displays full details of a specific item report without leaking sensitive student information."""

    model = Item
    template_name = "items/detail.html"
    context_object_name = "item"

    def get_queryset(self):
        return Item.objects.select_related("category", "location", "reported_by")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        item = self.object

        is_owner = user.is_authenticated and user.pk == item.reported_by_id
        is_admin = user.is_authenticated and getattr(user, "is_admin_user", False)

        context.update({
            "page_title": f"{item.get_item_type_display()}: {item.title}",
            "is_owner": is_owner,
            "is_admin": is_admin,
            "can_manage": is_owner or is_admin,
            "status_form": ItemStatusUpdateForm(instance=item) if is_admin else None,
        })
        return context


class ItemUpdateView(LoginRequiredMixin, UpdateView):
    """Allows the reporting user or an administrator to edit an item report."""

    model = Item
    form_class = ItemEditForm
    template_name = "items/edit.html"
    context_object_name = "item"

    def get_queryset(self):
        return Item.objects.select_related("category", "location", "reported_by")

    def dispatch(self, request, *args, **kwargs):
        item = self.get_object()
        user = request.user
        is_owner = user.is_authenticated and user.pk == item.reported_by_id
        is_admin = user.is_authenticated and getattr(user, "is_admin_user", False)

        if not (is_owner or is_admin):
            logger.warning("Unauthorized edit attempt on item %s by %s", item.id, user.email)
            raise PermissionDenied("You do not have permission to edit this report.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": f"Edit {self.object.get_item_type_display()} Item: {self.object.title}",
        })
        return context

    def form_valid(self, form):
        item = form.save()
        messages.success(self.request, f"Item report '{item.title}' updated successfully.")
        logger.info("Item %s updated by %s", item.id, self.request.user.email)
        return redirect(item.get_absolute_url())


class ItemDeleteView(LoginRequiredMixin, View):
    """POST-only deletion of an item report by its owner or an administrator.
    
    GET requests are rejected with 405 Method Not Allowed via http_method_names.
    """

    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        item = get_object_or_404(Item, pk=pk)
        user = request.user
        is_owner = user.pk == item.reported_by_id
        is_admin = getattr(user, "is_admin_user", False)

        if not (is_owner or is_admin):
            logger.warning("Unauthorized delete attempt on item %s by %s", item.id, user.email)
            raise PermissionDenied("You do not have permission to delete this report.")

        item_title = item.title
        image_to_delete = item.image

        with transaction.atomic():
            item.delete()

        # Clean up uploaded media file after successful database deletion
        if image_to_delete:
            try:
                image_to_delete.delete(save=False)
            except Exception as exc:
                logger.error("Failed to delete media for item %s: %s", pk, exc)

        messages.success(request, f"Report '{item_title}' has been deleted successfully.")
        logger.info("Item %s deleted by %s", pk, user.email)

        # Redirect to personal dashboard for students, or items catalog for admins
        if is_owner and not is_admin:
            return redirect("dashboard:student")
        return redirect("items:index")


class ItemStatusUpdateView(AdminRequiredMixin, View):
    """Admin-only view to update the operational status of an item report."""

    http_method_names = ["post"]

    def post(self, request, pk, *args, **kwargs):
        item = get_object_or_404(Item, pk=pk)
        form = ItemStatusUpdateForm(request.POST, instance=item)
        if form.is_valid():
            updated_item = form.save()
            messages.success(
                request,
                f"Status for '{updated_item.title}' updated to {updated_item.get_status_display()}.",
            )
            logger.info(
                "Item %s status changed to %s by admin %s",
                item.id,
                updated_item.status,
                request.user.email,
            )
        else:
            error_msg = form.errors.get("status", ["Invalid status choice or transition selected."])[0]
            messages.error(request, error_msg)
        return redirect(item.get_absolute_url())


def serve_item_image(request, filename):
    """Dynamic media server that fetches images directly from the database if missing on disk.
    
    Ensures that when the project runs on any device connected to the database,
    images are always rendered seamlessly even without manual file transfers.
    """
    import base64
    import os
    from django.conf import settings
    from django.http import FileResponse, Http404, HttpResponse
    from .models import StoredImage

    clean_name = os.path.basename(filename)
    disk_path = os.path.join(settings.MEDIA_ROOT, "item_images", clean_name)

    # 1. If file already exists on disk, serve it directly
    if os.path.exists(disk_path) and os.path.getsize(disk_path) > 0:
        return FileResponse(open(disk_path, "rb"), content_type="image/png")

    # 2. If missing on disk (e.g. on another device), retrieve from StoredImage in database
    stored = StoredImage.objects.filter(filename=clean_name).first()
    if not stored:
        stored = StoredImage.objects.filter(filename__endswith=clean_name).first()

    if stored and stored.image_base64:
        image_bytes = base64.b64decode(stored.image_base64)
        # Cache to local disk on this device for high-performance subsequent loads
        try:
            os.makedirs(os.path.dirname(disk_path), exist_ok=True)
            with open(disk_path, "wb") as f:
                f.write(image_bytes)
        except Exception as exc:
            logger.warning("Could not cache image to disk: %s", exc)
        return HttpResponse(image_bytes, content_type=stored.content_type)

    raise Http404("Image not found on disk or in database.")

