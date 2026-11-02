"""Tests for dashboard routing, dispatching, and role-based views."""
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

CampusUser = get_user_model()


class DashboardRoutingTests(TestCase):
    """Test dashboard views and role access."""

    def setUp(self):
        self.student = CampusUser.objects.create_user(
            username="student_dash@university.edu",
            email="student_dash@university.edu",
            password="Password123!",
            role=CampusUser.Role.STUDENT,
        )
        self.admin = CampusUser.objects.create_user(
            username="admin_dash@university.edu",
            email="admin_dash@university.edu",
            password="Password123!",
            role=CampusUser.Role.ADMIN,
        )
        self.super_admin = CampusUser.objects.create_user(
            username="super_dash@university.edu",
            email="super_dash@university.edu",
            password="Password123!",
            role=CampusUser.Role.SUPER_ADMIN,
        )

    def test_anonymous_redirected_to_login(self):
        """Unauthenticated user accessing /dashboard/ redirects to login."""
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, reverse("accounts:login"))

    def test_student_dashboard_renders(self):
        """Student dashboard renders successfully for authenticated student."""
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard:student"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Portal")

    def test_admin_dashboard_renders(self):
        """Admin dashboard renders successfully for authenticated administrator."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:admin"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Staff Console")

    def test_super_admin_dashboard_renders(self):
        """Super Admin dashboard renders successfully with system metrics."""
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("dashboard:super_admin"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Super Admin")
        self.assertContains(response, "Total Accounts")
