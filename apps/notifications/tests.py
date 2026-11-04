"""Unit and integration tests for the Notifications system."""
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import CampusUser
from apps.notifications.models import Notification, NotificationType, create_notification


class NotificationModelTests(TestCase):
    """Test Notification model and helper methods."""

    def setUp(self):
        self.user = CampusUser.objects.create_user(
            username="notify_user",
            email="notify@university.edu",
            password="TestPassword123!",
            role=CampusUser.Role.STUDENT,
        )

    def test_create_notification_helper(self):
        notification = create_notification(
            recipient=self.user,
            title="Item Matched",
            message="Your lost backpack has a potential match.",
            notification_type=NotificationType.MATCH_FOUND,
            target_url="/matching/hub/",
        )
        self.assertIsNotNone(notification.id)
        self.assertEqual(notification.recipient, self.user)
        self.assertFalse(notification.is_read)
        self.assertEqual(notification.notification_type, NotificationType.MATCH_FOUND)
        self.assertEqual(notification.target_url, "/matching/hub/")

    def test_mark_as_read(self):
        notification = create_notification(
            recipient=self.user,
            title="Test Alert",
            message="Alert content",
        )
        self.assertFalse(notification.is_read)
        notification.mark_as_read()
        self.assertTrue(notification.is_read)


class NotificationViewsTests(TestCase):
    """Test notification list and mark-as-read actions."""

    def setUp(self):
        self.user1 = CampusUser.objects.create_user(
            username="student1",
            email="s1@university.edu",
            password="TestPassword123!",
            role=CampusUser.Role.STUDENT,
        )
        self.user2 = CampusUser.objects.create_user(
            username="student2",
            email="s2@university.edu",
            password="TestPassword123!",
            role=CampusUser.Role.STUDENT,
        )
        self.n1 = create_notification(self.user1, "Notice 1", "Body 1")
        self.n2 = create_notification(self.user1, "Notice 2", "Body 2")
        self.n3 = create_notification(self.user2, "Notice 3", "Body 3")

    def test_login_required(self):
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 302)

    def test_list_view_shows_user_notifications_only(self):
        self.client.login(username="student1", password="TestPassword123!")
        response = self.client.get(reverse("notifications:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Notice 1")
        self.assertContains(response, "Notice 2")
        self.assertNotContains(response, "Notice 3")

    def test_mark_single_read(self):
        self.client.login(username="student1", password="TestPassword123!")
        response = self.client.post(
            reverse("notifications:mark_read", kwargs={"pk": self.n1.id})
        )
        self.assertEqual(response.status_code, 302)
        self.n1.refresh_from_db()
        self.assertTrue(self.n1.is_read)

    def test_user_cannot_mark_other_user_notification(self):
        self.client.login(username="student1", password="TestPassword123!")
        # Attempt to mark user2's notification
        response = self.client.post(
            reverse("notifications:mark_read", kwargs={"pk": self.n3.id})
        )
        self.assertEqual(response.status_code, 404)
        self.n3.refresh_from_db()
        self.assertFalse(self.n3.is_read)

    def test_mark_all_read(self):
        self.client.login(username="student1", password="TestPassword123!")
        response = self.client.post(reverse("notifications:mark_all_read"))
        self.assertEqual(response.status_code, 302)
        self.n1.refresh_from_db()
        self.n2.refresh_from_db()
        self.assertTrue(self.n1.is_read)
        self.assertTrue(self.n2.is_read)
        # user2's notification remains unread
        self.n3.refresh_from_db()
        self.assertFalse(self.n3.is_read)
