from django.test import TestCase
from django.urls import reverse


class MatchingRoutingTests(TestCase):
    """Test URL routing and placeholder responses for matching app."""

    def test_matching_index_resolves(self):
        response = self.client.get(reverse("matching:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Semantic Matching")
