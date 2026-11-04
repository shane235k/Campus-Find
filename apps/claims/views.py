"""Class-based views for ownership claims, student tracking, and administrative review."""
import logging
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.accounts.permissions import AdminRequiredMixin
from apps.items.models import Item
from apps.matching.models import PotentialMatch, MatchStatus
from .forms import ClaimSubmissionForm, ClaimReviewForm
from .models import Claim, ClaimStatus
from .services import (
    submit_claim,
    mark_claim_under_review,
    approve_claim,
    reject_claim,
    withdraw_claim,
)

logger = logging.getLogger(__name__)


class ClaimSubmissionView(LoginRequiredMixin, FormView):
    """Student entry point to submit ownership proof for a lost or found report."""

    template_name = "claims/submit_claim.html"
    form_class = ClaimSubmissionForm

    def get_item(self):
        item_id = self.kwargs.get("item_id")
        return get_object_or_404(
            Item.objects.select_related("category", "location", "reported_by"),
            id=item_id,
        )

    def get_potential_match(self):
        match_id = self.request.GET.get("match_id")
        if match_id:
            try:
                return PotentialMatch.objects.filter(id=match_id).first()
            except Exception:
                return None
        return None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)

        item = self.get_item()
        user = request.user

        # Validation: reporter cannot claim own item
        if item.reported_by == user:
            messages.warning(request, "You cannot submit an ownership claim for an item you reported yourself.")
            return redirect("items:detail", pk=item.id)

        # Validation: cannot claim resolved or closed item
        if item.status in [Item.ItemStatus.RESOLVED, Item.ItemStatus.CLOSED]:
            messages.warning(request, f"This item is already {item.get_status_display().lower()} and cannot be claimed.")
            return redirect("items:detail", pk=item.id)

        # Validation: active claim already exists
        existing = Claim.objects.filter(
            claimant=user,
            item=item,
            status__in=[ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW],
        ).first()
        if existing:
            messages.info(request, f"You already have an active claim (#{str(existing.id)[:8]}) pending review for this item.")
            return redirect("claims:detail", claim_id=existing.id)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "item": self.get_item(),
            "potential_match": self.get_potential_match(),
            "page_title": f"File Ownership Claim — {self.get_item().title}",
        })
        return context

    def form_valid(self, form):
        item = self.get_item()
        potential_match = self.get_potential_match()
        user = self.request.user

        try:
            claim = submit_claim(
                claimant=user,
                item=item,
                claim_description=form.cleaned_data["claim_description"],
                distinguishing_features=form.cleaned_data["distinguishing_features"],
                item_contents=form.cleaned_data.get("item_contents", ""),
                last_seen_details=form.cleaned_data.get("last_seen_details", ""),
                evidence_file=self.request.FILES.get("evidence_file"),
                potential_match=potential_match,
            )
            messages.success(
                self.request,
                f"Ownership claim #{str(claim.id)[:8]} successfully filed! Campus operations desk will review your private proof.",
            )
            return redirect("claims:detail", claim_id=claim.id)
        except ValidationError as exc:
            form.add_error(None, exc.message if hasattr(exc, "message") else str(exc))
            return self.form_invalid(form)


class ClaimDetailView(LoginRequiredMixin, DetailView):
    """View details, status timeline, and review outcomes of a specific claim."""

    model = Claim
    template_name = "claims/claim_detail.html"
    context_object_name = "claim"
    pk_url_kwarg = "claim_id"

    def get_queryset(self):
        return Claim.objects.select_related(
            "claimant",
            "item",
            "item__category",
            "item__location",
            "item__reported_by",
            "potential_match",
            "reviewed_by",
        )

    def dispatch(self, request, *args, **kwargs):
        claim = self.get_object()
        user = request.user
        is_owner = claim.claimant == user
        is_admin = user.is_staff or getattr(user, "is_admin_user", False)

        if not (is_owner or is_admin):
            raise PermissionDenied("You do not have permission to view this confidential claim.")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        claim = self.object
        context.update({
            "is_admin": user.is_staff or getattr(user, "is_admin_user", False),
            "can_withdraw": claim.can_withdraw(user),
            "page_title": f"Claim #{str(claim.id)[:8]} Details",
        })
        return context


class ClaimWithdrawView(LoginRequiredMixin, View):
    """POST-only view allowing claimant to withdraw their active claim."""

    http_method_names = ["post"]

    def post(self, request, claim_id):
        claim = get_object_or_404(Claim, id=claim_id)
        try:
            withdraw_claim(claim, request.user)
            messages.success(request, f"Claim #{str(claim.id)[:8]} has been withdrawn.")
        except ValidationError as exc:
            messages.error(request, str(exc))
        return redirect("claims:detail", claim_id=claim.id)


class StudentClaimsListView(LoginRequiredMixin, ListView):
    """Personal list of all claims filed by the current authenticated student."""

    model = Claim
    template_name = "claims/my_claims.html"
    context_object_name = "claims"
    paginate_by = 10

    def get_queryset(self):
        status_filter = self.request.GET.get("status")
        qs = Claim.objects.filter(claimant=self.request.user).select_related(
            "item", "item__category", "item__location", "reviewed_by"
        ).order_by("-created_at")

        if status_filter and status_filter in ClaimStatus.values:
            qs = qs.filter(status=status_filter)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_qs = Claim.objects.filter(claimant=self.request.user)
        context.update({
            "page_title": "My Ownership Claims",
            "total_claims": base_qs.count(),
            "active_claims": base_qs.filter(status__in=[ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW]).count(),
            "approved_claims": base_qs.filter(status=ClaimStatus.APPROVED).count(),
            "rejected_claims": base_qs.filter(status=ClaimStatus.REJECTED).count(),
            "current_status": self.request.GET.get("status", ""),
            "claim_statuses": ClaimStatus.choices,
        })
        return context


class AdminClaimsDashboardView(AdminRequiredMixin, ListView):
    """Staff administrator console: queue of all submitted ownership claims across campus."""

    model = Claim
    template_name = "claims/admin_dashboard.html"
    context_object_name = "claims"
    paginate_by = 15

    def get_queryset(self):
        qs = Claim.objects.select_related(
            "claimant",
            "item",
            "item__category",
            "item__location",
            "reviewed_by",
        ).order_by("-created_at")

        status_filter = self.request.GET.get("status")
        if status_filter and status_filter in ClaimStatus.values:
            qs = qs.filter(status=status_filter)

        search_query = self.request.GET.get("q")
        if search_query:
            qs = qs.filter(
                Q(claimant__username__icontains=search_query) |
                Q(claimant__email__icontains=search_query) |
                Q(item__title__icontains=search_query) |
                Q(claim_description__icontains=search_query) |
                Q(distinguishing_features__icontains=search_query)
            )

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        counts = Claim.objects.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(status=ClaimStatus.PENDING)),
            under_review=Count("id", filter=Q(status=ClaimStatus.UNDER_REVIEW)),
            approved=Count("id", filter=Q(status=ClaimStatus.APPROVED)),
            rejected=Count("id", filter=Q(status=ClaimStatus.REJECTED)),
            withdrawn=Count("id", filter=Q(status=ClaimStatus.WITHDRAWN)),
        )

        context.update({
            "page_title": "Admin Claims Moderation Console",
            "total_count": counts["total"] or 0,
            "pending_count": counts["pending"] or 0,
            "under_review_count": counts["under_review"] or 0,
            "approved_count": counts["approved"] or 0,
            "rejected_count": counts["rejected"] or 0,
            "withdrawn_count": counts["withdrawn"] or 0,
            "current_status": self.request.GET.get("status", ""),
            "search_query": self.request.GET.get("q", ""),
            "claim_statuses": ClaimStatus.choices,
        })
        return context


class AdminClaimReviewView(AdminRequiredMixin, DetailView):
    """Detailed verification portal for campus staff to inspect evidence and approve/reject claims."""

    model = Claim
    template_name = "claims/admin_review.html"
    context_object_name = "claim"
    pk_url_kwarg = "claim_id"

    def get_queryset(self):
        return Claim.objects.select_related(
            "claimant",
            "item",
            "item__category",
            "item__location",
            "item__reported_by",
            "potential_match",
            "reviewed_by",
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        claim = self.object
        
        # Competing claims for the exact same item
        competing_claims = Claim.objects.filter(
            item=claim.item
        ).exclude(id=claim.id).select_related("claimant", "reviewed_by").order_by("-created_at")

        context.update({
            "review_form": ClaimReviewForm(initial={"admin_notes": claim.admin_notes}),
            "competing_claims": competing_claims,
            "competing_count": competing_claims.count(),
            "page_title": f"Review Claim #{str(claim.id)[:8]} — {claim.item.title}",
        })
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        claim = self.object
        form = ClaimReviewForm(request.POST)

        if not form.is_valid():
            context = self.get_context_data()
            context["review_form"] = form
            return render(request, self.template_name, context)

        action = form.cleaned_data["action"]
        admin_notes = form.cleaned_data.get("admin_notes", "")
        rejection_reason = form.cleaned_data.get("rejection_reason", "")

        try:
            if action == "under_review":
                mark_claim_under_review(claim, request.user, admin_notes=admin_notes)
                messages.info(request, f"Claim #{str(claim.id)[:8]} moved to Under Review.")
            elif action == "approve":
                approve_claim(claim, request.user, admin_notes=admin_notes)
                messages.success(
                    request,
                    f"Claim #{str(claim.id)[:8]} APPROVED! Item '{claim.item.title}' marked as RESOLVED and ownership verified."
                )
            elif action == "reject":
                reject_claim(claim, request.user, rejection_reason=rejection_reason, admin_notes=admin_notes)
                messages.warning(
                    request,
                    f"Claim #{str(claim.id)[:8]} REJECTED. Student notified with specified reason."
                )
            return redirect("claims:admin_review", claim_id=claim.id)
        except ValidationError as exc:
            messages.error(request, str(exc))
            return redirect("claims:admin_review", claim_id=claim.id)
