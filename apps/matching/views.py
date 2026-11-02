"""Views for AI Semantic Matching Engine."""
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.items.models import Item
from .models import PotentialMatch, MatchStatus

ItemType = Item.ItemType
ItemStatus = Item.ItemStatus
from .services import (
    find_and_generate_matches_for_item,
    run_system_wide_matching,
    is_model_available,
    MODEL_NAME,
)

logger = logging.getLogger(__name__)


class MatchingHubView(LoginRequiredMixin, ListView):
    """Central Matching Hub displaying ranked potential matches for the user or administrator."""
    model = PotentialMatch
    template_name = "matching/hub.html"
    context_object_name = "matches"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        status_filter = self.request.GET.get("status")
        
        # Base queryset: admins view all; students view only their own items
        if user.is_staff or getattr(user, "is_admin_user", False):
            qs = PotentialMatch.objects.all()
        else:
            qs = PotentialMatch.objects.filter(
                Q(lost_item__reported_by=user) | Q(found_item__reported_by=user)
            )

        # Exclude matches involving items that were subsequently resolved or closed
        qs = qs.exclude(
            Q(lost_item__status__in=[ItemStatus.RESOLVED, ItemStatus.CLOSED]) |
            Q(found_item__status__in=[ItemStatus.RESOLVED, ItemStatus.CLOSED])
        )

        if status_filter and status_filter in MatchStatus.values:
            qs = qs.filter(status=status_filter)

        return qs.select_related(
            "lost_item",
            "found_item",
            "lost_item__category",
            "found_item__category",
            "lost_item__location",
            "found_item__location",
            "lost_item__reported_by",
            "found_item__reported_by",
        ).order_by("-final_score", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Determine user scope for stats
        if user.is_staff or getattr(user, "is_admin_user", False):
            base_qs = PotentialMatch.objects.all()
            user_items = Item.objects.filter(status__in=[ItemStatus.OPEN, ItemStatus.CLAIM_PENDING])
        else:
            base_qs = PotentialMatch.objects.filter(
                Q(lost_item__reported_by=user) | Q(found_item__reported_by=user)
            )
            user_items = Item.objects.filter(
                reported_by=user,
                status__in=[ItemStatus.OPEN, ItemStatus.CLAIM_PENDING],
            )

        model_ok, model_msg = is_model_available()

        context.update({
            "total_matches": base_qs.count(),
            "high_confidence_matches": base_qs.filter(final_score__gte=0.70).count(),
            "suggested_count": base_qs.filter(status=MatchStatus.SUGGESTED).count(),
            "interested_count": base_qs.filter(status=MatchStatus.INTERESTED).count(),
            "dismissed_count": base_qs.filter(status=MatchStatus.DISMISSED).count(),
            "active_user_items": user_items.order_by("-created_at")[:8],
            "current_status": self.request.GET.get("status", ""),
            "model_name": MODEL_NAME,
            "model_operational": model_ok,
            "model_status_message": model_msg,
            "match_statuses": MatchStatus.choices,
        })
        return context


class ItemMatchesView(LoginRequiredMixin, ListView):
    """View all potential matches for a specific item report."""
    model = PotentialMatch
    template_name = "matching/item_matches.html"
    context_object_name = "matches"
    paginate_by = 10

    def get_item(self):
        item_id = self.kwargs.get("item_id")
        return get_object_or_404(
            Item.objects.select_related("category", "location", "reported_by"),
            id=item_id,
        )

    def dispatch(self, request, *args, **kwargs):
        item = self.get_item()
        user = request.user
        # Only item owner or staff can view item matches
        if not (user.is_staff or getattr(user, "is_admin_user", False) or item.reported_by == user):
            raise PermissionDenied("You do not have permission to view matches for this item.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        item = self.get_item()
        if item.item_type == ItemType.LOST:
            qs = PotentialMatch.objects.filter(lost_item=item)
        else:
            qs = PotentialMatch.objects.filter(found_item=item)

        return qs.select_related(
            "lost_item",
            "found_item",
            "lost_item__category",
            "found_item__category",
            "lost_item__location",
            "found_item__location",
            "lost_item__reported_by",
            "found_item__reported_by",
        ).order_by("-final_score", "-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        item = self.get_item()
        model_ok, model_msg = is_model_available()
        context.update({
            "target_item": item,
            "model_name": MODEL_NAME,
            "model_operational": model_ok,
        })
        return context


class MatchDetailView(LoginRequiredMixin, DetailView):
    """Deep inspection view comparing LOST and FOUND items side-by-side with scoring breakdown."""
    model = PotentialMatch
    template_name = "matching/match_detail.html"
    context_object_name = "match"
    pk_url_kwarg = "match_id"

    def get_queryset(self):
        return PotentialMatch.objects.select_related(
            "lost_item",
            "found_item",
            "lost_item__category",
            "found_item__category",
            "lost_item__location",
            "found_item__location",
            "lost_item__reported_by",
            "found_item__reported_by",
        )

    def dispatch(self, request, *args, **kwargs):
        match_obj = self.get_object()
        user = request.user
        is_owner = (match_obj.lost_item.reported_by == user or match_obj.found_item.reported_by == user)
        is_admin = user.is_staff or getattr(user, "is_admin_user", False)
        if not (is_owner or is_admin):
            raise PermissionDenied("You do not have permission to view this match comparison.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        match_obj = self.object
        
        # Percentage representations for visual UI progress bars
        context.update({
            "final_percentage": int(round(match_obj.final_score * 100)),
            "desc_percentage": int(round(match_obj.description_similarity * 100)),
            "title_percentage": int(round(match_obj.title_similarity * 100)),
            "category_percentage": int(round(match_obj.category_score * 100)),
            "location_percentage": int(round(match_obj.location_score * 100)),
            "date_percentage": int(round(match_obj.date_score * 100)),
            "days_difference": abs((match_obj.lost_item.date_lost_or_found - match_obj.found_item.date_lost_or_found).days),
        })
        return context


class MatchActionView(LoginRequiredMixin, View):
    """POST-only view to update a match's status (Express Interest, Dismiss)."""
    http_method_names = ["post"]

    def post(self, request, match_id):
        match_obj = get_object_or_404(PotentialMatch, id=match_id)
        user = request.user
        is_owner = (match_obj.lost_item.reported_by == user or match_obj.found_item.reported_by == user)
        is_admin = user.is_staff or getattr(user, "is_admin_user", False)
        
        if not (is_owner or is_admin):
            raise PermissionDenied("You do not have permission to update this match status.")

        action = request.POST.get("action")
        if action == "interested":
            match_obj.status = MatchStatus.INTERESTED
            match_obj.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Expressed interest in match #{str(match_obj.id)[:8]}! Proceed to Claim Verification in Phase 4.")
        elif action == "dismiss":
            match_obj.status = MatchStatus.DISMISSED
            match_obj.save(update_fields=["status", "updated_at"])
            messages.info(request, f"Match #{str(match_obj.id)[:8]} has been dismissed.")
        elif action == "reset":
            match_obj.status = MatchStatus.SUGGESTED
            match_obj.save(update_fields=["status", "updated_at"])
            messages.info(request, f"Match #{str(match_obj.id)[:8]} status reset to Suggested.")
        else:
            messages.warning(request, "Invalid match action requested.")

        next_url = request.POST.get("next") or reverse("matching:match_detail", kwargs={"match_id": match_obj.id})
        return redirect(next_url)


class TriggerMatchingView(LoginRequiredMixin, View):
    """POST-only view to trigger actual semantic matching for an item or platform-wide."""
    http_method_names = ["post"]

    def post(self, request, item_id=None):
        user = request.user
        
        if item_id:
            # Item-specific matching trigger
            item = get_object_or_404(Item, id=item_id)
            if not (user.is_staff or getattr(user, "is_admin_user", False) or item.reported_by == user):
                raise PermissionDenied("You do not have permission to run matching for this item.")

            matches = find_and_generate_matches_for_item(item, min_score=0.30)
            if matches:
                messages.success(
                    request,
                    f"AI Matching Engine evaluated candidates: {len(matches)} potential match(es) identified for '{item.title}'!"
                )
            else:
                messages.info(
                    request,
                    f"Scan complete. No candidate matches currently meet the similarity threshold for '{item.title}'."
                )
            return redirect(reverse("matching:item_matches", kwargs={"item_id": item.id}))
        else:
            # System-wide scan (admins or student running scan across their active reports)
            if user.is_staff or getattr(user, "is_admin_user", False):
                summary = run_system_wide_matching(min_score=0.30)
                messages.success(
                    request,
                    f"System-Wide AI Scan Complete: Processed {summary['processed_items']} items, generated {summary['total_matches']} match links."
                )
            else:
                # Run for current student's open reports
                user_items = Item.objects.filter(reported_by=user, status__in=[ItemStatus.OPEN, ItemStatus.CLAIM_PENDING])
                count = 0
                for it in user_items:
                    m = find_and_generate_matches_for_item(it, min_score=0.30)
                    count += len(m)
                messages.success(
                    request,
                    f"Scanned all your active reports: {count} potential match(es) identified or updated!"
                )
            return redirect(reverse("matching:hub"))
