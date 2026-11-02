from django.test import TestCase
from django.urls import reverse


class DashboardRoutingTests(TestCase):
    """Test URL routing and placeholder responses for dashboard app."""

    def test_dashboard_index_resolves(self):
        response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Control Center")
