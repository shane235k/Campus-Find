"""Views for student, admin, and super-admin dashboards."""
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.views.generic import TemplateView

from apps.accounts.models import CampusUser
from apps.accounts.permissions import (
    AdminRequiredMixin,
    StudentRequiredMixin,
    SuperAdminRequiredMixin,
)
from apps.claims.models import Claim, ClaimStatus
from apps.items.models import CampusLocation, Category, Item
from apps.matching.models import PotentialMatch


class DashboardDispatcher(TemplateView):
    """Dispatches authenticated users to their designated role dashboard."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if request.user.role == CampusUser.Role.SUPER_ADMIN:
            return redirect("dashboard:super_admin")
        elif request.user.role == CampusUser.Role.ADMIN:
            return redirect("dashboard:admin")
        return redirect("dashboard:student")


class StudentDashboardView(StudentRequiredMixin, TemplateView):
    """Personal student portal: real database stats, recent reports, and recovery tracking."""

    template_name = "dashboard/student.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Fetch aggregate counts using Django ORM
        user_items = user.reported_items.all()
        counts = user_items.aggregate(
            total=Count("id"),
            lost=Count("id", filter=Q(item_type=Item.ItemType.LOST)),
            found=Count("id", filter=Q(item_type=Item.ItemType.FOUND)),
            open=Count("id", filter=Q(status=Item.ItemStatus.OPEN)),
            resolved=Count("id", filter=Q(status=Item.ItemStatus.RESOLVED)),
        )

        recent_reports = user_items.select_related("category", "location").order_by("-created_at")[:8]

        # Phase 3 AI Matches count for student
        student_matches = PotentialMatch.objects.filter(
            Q(lost_item__reported_by=user) | Q(found_item__reported_by=user)
        ).exclude(
            Q(lost_item__status__in=[Item.ItemStatus.RESOLVED, Item.ItemStatus.CLOSED]) |
            Q(found_item__status__in=[Item.ItemStatus.RESOLVED, Item.ItemStatus.CLOSED])
        )

        # Phase 4 Claims for student
        user_claims = Claim.objects.filter(claimant=user).select_related("item", "item__category")
        claims_count = user_claims.count()
        active_claims_count = user_claims.filter(
            status__in=[ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW]
        ).count()
        recent_claims = user_claims.order_by("-created_at")[:5]

        context.update({
            "page_title": "Student Dashboard",
            "active_tab": "dashboard",
            "total_reports": counts["total"] or 0,
            "lost_reports": counts["lost"] or 0,
            "found_reports": counts["found"] or 0,
            "open_reports": counts["open"] or 0,
            "resolved_reports": counts["resolved"] or 0,
            "potential_matches_count": student_matches.count(),
            "recent_reports": recent_reports,
            "claims_count": claims_count,
            "active_claims_count": active_claims_count,
            "recent_claims": recent_claims,
        })
        return context


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """Administrator moderation console: system inventory, queue stats, and item oversight."""

    template_name = "dashboard/admin.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        counts = Item.objects.aggregate(
            total=Count("id"),
            lost=Count("id", filter=Q(item_type=Item.ItemType.LOST)),
            found=Count("id", filter=Q(item_type=Item.ItemType.FOUND)),
            open=Count("id", filter=Q(status=Item.ItemStatus.OPEN)),
            resolved=Count("id", filter=Q(status=Item.ItemStatus.RESOLVED)),
            claim_pending=Count("id", filter=Q(status=Item.ItemStatus.CLAIM_PENDING)),
        )

        recent_items = (
            Item.objects.select_related("category", "location", "reported_by")
            .order_by("-created_at")[:12]
        )

        # Phase 3 AI Matches counts for admin operations
        platform_matches = PotentialMatch.objects.all()

        # Phase 4 Claims queue metrics
        total_claims_count = Claim.objects.count()
        pending_claims_count = Claim.objects.filter(
            status__in=[ClaimStatus.PENDING, ClaimStatus.UNDER_REVIEW]
        ).count()

        context.update({
            "page_title": "Administrator Operations Console",
            "active_tab": "admin_dashboard",
            "total_items": counts["total"] or 0,
            "lost_items": counts["lost"] or 0,
            "found_items": counts["found"] or 0,
            "open_items": counts["open"] or 0,
            "resolved_items": counts["resolved"] or 0,
            "claim_pending_items": counts["claim_pending"] or 0,
            "categories_count": Category.objects.count(),
            "locations_count": CampusLocation.objects.count(),
            "total_matches_count": platform_matches.count(),
            "high_confidence_matches_count": platform_matches.filter(final_score__gte=0.70).count(),
            "total_claims_count": total_claims_count,
            "pending_claims_count": pending_claims_count,
            "recent_items": recent_items,
        })
        return context


class SuperAdminDashboardView(SuperAdminRequiredMixin, TemplateView):
    """Super Administrator command center."""

    template_name = "dashboard/super_admin.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            "page_title": "Super Administrator Command Center",
            "active_tab": "super_admin_dashboard",
            "total_users": CampusUser.objects.count(),
            "student_count": CampusUser.objects.filter(role=CampusUser.Role.STUDENT).count(),
            "admin_count": CampusUser.objects.filter(role=CampusUser.Role.ADMIN).count(),
            "total_items": Item.objects.count(),
        })
        return context
