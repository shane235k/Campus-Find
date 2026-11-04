"""Views for user notifications."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from .models import Notification


class NotificationListView(LoginRequiredMixin, ListView):
    """Display in-app notifications for the authenticated user."""
    model = Notification
    template_name = "notifications/list.html"
    context_object_name = "notifications"
    paginate_by = 15

    def get_queryset(self):
        return Notification.objects.filter(recipient=self.request.user).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user_notifications = Notification.objects.filter(recipient=self.request.user)
        context.update({
            "page_title": "My Notifications",
            "unread_count": user_notifications.filter(is_read=False).count(),
            "total_count": user_notifications.count(),
        })
        return context


class MarkNotificationReadView(LoginRequiredMixin, View):
    """Mark a single notification as read and optionally redirect to its target_url."""
    http_method_names = ["post"]

    def post(self, request, pk):
        notification = get_object_or_404(Notification, id=pk, recipient=request.user)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        
        target = request.POST.get("next") or notification.target_url or reverse("notifications:list")
        return redirect(target)


class MarkAllNotificationsReadView(LoginRequiredMixin, View):
    """Mark all notifications for the user as read."""
    http_method_names = ["post"]

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect(reverse("notifications:list"))
