from django.test import TestCase
from django.urls import reverse


class ItemsRoutingTests(TestCase):
    """Test URL routing and placeholder responses for items app."""

    def test_items_index_resolves(self):
        response = self.client.get(reverse("items:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Items Directory")

    def test_report_lost_resolves(self):
        response = self.client.get(reverse("items:report_lost"))
        self.assertEqual(response.status_code, 200)

    def test_report_found_resolves(self):
        response = self.client.get(reverse("items:report_found"))
        self.assertEqual(response.status_code, 200)
