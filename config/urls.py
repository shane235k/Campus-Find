"""Campus Lost & Found Hub URL Configuration.

Phase 0 URL Architecture.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from config.views import HomeView

urlpatterns = [
    # Administration
    path("admin/", admin.site.urls),

    # Public Landing Page
    path("", HomeView.as_view(), name="home"),

    # Namespaced Modular Applications
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    path("items/", include("apps.items.urls", namespace="items")),
    path("matching/", include("apps.matching.urls", namespace="matching")),
    path("claims/", include("apps.claims.urls", namespace="claims")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("dashboard/", include("apps.dashboard.urls", namespace="dashboard")),
    path("api/v1/", include("apps.items.api_urls", namespace="api_v1")),
]

# Serve media and static files in development mode
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
