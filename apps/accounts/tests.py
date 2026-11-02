from django.test import TestCase
from django.urls import reverse


class AccountsRoutingTests(TestCase):
    """Test URL routing and placeholder responses for accounts app."""

    def test_accounts_index_resolves(self):
        response = self.client.get(reverse("accounts:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Accounts")

    def test_login_placeholder_resolves(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)

    def test_register_placeholder_resolves(self):
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
