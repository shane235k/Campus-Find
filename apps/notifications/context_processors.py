"""Context processors for notifications application."""


def notification_stats(request):
    """Exposes unread notification count across all templates for authenticated users."""
    if hasattr(request, "user") and request.user.is_authenticated:
        try:
            count = request.user.notifications.filter(is_read=False).count()
            return {"unread_notifications_count": count}
        except Exception:
            return {"unread_notifications_count": 0}
    return {"unread_notifications_count": 0}

