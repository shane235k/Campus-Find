from django.test import TestCase
from django.urls import reverse


class NotificationsRoutingTests(TestCase):
    """Test URL routing and placeholder responses for notifications app."""

    def test_notifications_index_resolves(self):
        response = self.client.get(reverse("notifications:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notification Center")
