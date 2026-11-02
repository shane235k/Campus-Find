from django.test import TestCase
from django.urls import reverse


class HomeLandingPageTests(TestCase):
    """Test public landing page and branding."""

    def test_landing_page_status_code(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_landing_page_branding(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Campus Lost &amp; Found Hub")
        self.assertContains(response, "Lost Something on Campus?")

    def test_landing_page_report_actions(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "Report Lost Item")
        self.assertContains(response, "Report Found Item")

    def test_landing_page_empty_state(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "No Items Reported Yet")

    def test_landing_page_static_references(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, "/static/css/main.css")
        self.assertContains(response, "/static/js/main.js")
        self.assertContains(response, "/static/images/logo.svg")
