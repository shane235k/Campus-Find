from django.test import TestCase
from django.urls import reverse


class ClaimsRoutingTests(TestCase):
    """Test URL routing and placeholder responses for claims app."""

    def test_claims_index_resolves(self):
        response = self.client.get(reverse("claims:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Claims")
