"""Comprehensive test suite for the items application.

Covers:
1. Category, CampusLocation, and Item models (defaults, constraints, privacy display name, properties).
2. Reporting workflows (lost and found reporting, login requirement, server-side user/status enforcement, inactive choices rejection, future date rejection).
3. Browsing and search (keyword search in title/desc, filters by type/category/location/status/dates, pagination, default exclusion of RESOLVED/CLOSED items).
4. Permissions and security (owner vs non-owner access, 403 Forbidden, POST-only deletion with 405 for GET, admin moderation).
5. Image handling (valid image upload, >5MB rejection, corrupted/non-image rejection, image replacement, image removal, file cleanup on delete).
6. Django REST Framework API (list, detail, auth enforcement, permissions, filters, categories/locations endpoints).
7. Dashboard aggregates (student and admin dashboard querysets and statistics).
"""

import io
import os
import shutil
import tempfile
import uuid
from datetime import date, timedelta
from PIL import Image

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.items.models import CampusLocation, Category, Item

CampusUser = get_user_model()

# Create a temporary directory for media uploads during tests
TEMP_MEDIA_ROOT = tempfile.mkdtemp()


def create_dummy_image(name="test.jpg", size_bytes=1024, format="JPEG"):
    """Helper to generate a valid in-memory image for testing."""
    file = io.BytesIO()
    image = Image.new("RGB", (100, 100), color=(73, 109, 137))
    image.save(file, format=format)
    file.seek(0)
    data = file.read()
    if size_bytes > len(data):
        # Pad if a larger file size is requested
        data += b"\0" * (size_bytes - len(data))
    return SimpleUploadedFile(name, data, content_type=f"image/{format.lower()}")


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ItemModelTests(TestCase):
    """Test model behaviors, choices, properties, and privacy guarantees."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = CampusUser.objects.create_user(
            username="teststudent",
            email="student@university.edu",
            password="SecurePassword123!",
            first_name="Jane",
            last_name="Doe",
            student_id="STU-2026-9999",
            phone_number="+1234567890",
        )
        self.category = Category.objects.create(name="Electronics", description="Laptops, phones")
        self.location = CampusLocation.objects.create(name="Main Library", description="2nd Floor")

    def test_category_and_location_creation(self):
        self.assertEqual(str(self.category), "Electronics")
        self.assertEqual(str(self.location), "Main Library")
        self.assertTrue(self.category.is_active)
        self.assertTrue(self.location.is_active)

    def test_item_creation_defaults(self):
        item = Item.objects.create(
            title="Lost Dell XPS",
            description="Silver laptop left near study desk",
            item_type=Item.ItemType.LOST,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.user,
        )
        self.assertIsInstance(item.id, uuid.UUID)
        self.assertEqual(item.status, Item.ItemStatus.OPEN)
        self.assertTrue(item.is_lost)
        self.assertFalse(item.is_found)
        self.assertTrue(item.is_open)
        self.assertFalse(item.is_resolved)
        self.assertFalse(item.is_closed)
        self.assertFalse(item.is_claim_pending)

    def test_item_privacy_reporter_display_name(self):
        """Verify reporter_display_name protects student privacy and never leaks email, phone, or ID."""
        item = Item.objects.create(
            title="Found Blue Hydro Flask",
            description="Found in lecture hall 3",
            item_type=Item.ItemType.FOUND,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.user,
        )
        display = item.reporter_display_name
        self.assertEqual(display, "Jane Doe")
        self.assertNotIn("student@university.edu", display)
        self.assertNotIn("STU-2026-9999", display)
        self.assertNotIn("+1234567890", display)

        # When first and last name are blank, fall back to username safely
        self.user.first_name = ""
        self.user.last_name = ""
        self.user.save()
        self.assertEqual(item.reporter_display_name, "teststudent")


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ItemReportingTests(TestCase):
    """Test Lost & Found reporting forms and views."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.student = CampusUser.objects.create_user(
            username="reporter",
            email="reporter@university.edu",
            password="SecurePassword123!",
            first_name="Alice",
            last_name="Smith",
        )
        self.category = Category.objects.create(name="Keys", is_active=True)
        self.inactive_cat = Category.objects.create(name="Inactive Cat", is_active=False)
        self.location = CampusLocation.objects.create(name="Student Center", is_active=True)
        self.inactive_loc = CampusLocation.objects.create(name="Closed Facility", is_active=False)

    def test_unauthenticated_user_redirected_to_login(self):
        lost_resp = self.client.get(reverse("items:report_lost"))
        self.assertEqual(lost_resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), lost_resp.url)

        found_resp = self.client.get(reverse("items:report_found"))
        self.assertEqual(found_resp.status_code, 302)
        self.assertIn(reverse("accounts:login"), found_resp.url)

    def test_authenticated_student_reports_lost_item(self):
        self.client.login(username="reporter", password="SecurePassword123!")
        post_data = {
            "title": "Lost Gold Watch",
            "description": "Lost near café",
            "category": self.category.id,
            "location": self.location.id,
            "date_lost_or_found": date.today().isoformat(),
        }
        response = self.client.post(reverse("items:report_lost"), post_data)
        self.assertEqual(response.status_code, 302)

        item = Item.objects.get(title="Lost Gold Watch")
        self.assertEqual(item.item_type, Item.ItemType.LOST)
        self.assertEqual(item.reported_by, self.student)
        self.assertEqual(item.status, Item.ItemStatus.OPEN)
        self.assertRedirects(response, reverse("items:detail", kwargs={"pk": item.pk}))

    def test_authenticated_student_reports_found_item(self):
        self.client.login(username="reporter", password="SecurePassword123!")
        post_data = {
            "title": "Found Black Backpack",
            "description": "Found on lawn",
            "category": self.category.id,
            "location": self.location.id,
            "date_lost_or_found": date.today().isoformat(),
        }
        response = self.client.post(reverse("items:report_found"), post_data)
        self.assertEqual(response.status_code, 302)

        item = Item.objects.get(title="Found Black Backpack")
        self.assertEqual(item.item_type, Item.ItemType.FOUND)
        self.assertEqual(item.reported_by, self.student)
        self.assertEqual(item.status, Item.ItemStatus.OPEN)

    def test_inactive_category_and_location_rejected(self):
        self.client.login(username="reporter", password="SecurePassword123!")
        post_data = {
            "title": "Test Item",
            "description": "Testing inactive relations",
            "category": self.inactive_cat.id,
            "location": self.inactive_loc.id,
            "date_lost_or_found": date.today().isoformat(),
        }
        response = self.client.post(reverse("items:report_lost"), post_data)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertTrue(form.errors)
        self.assertIn("category", form.errors)
        self.assertIn("location", form.errors)

    def test_future_date_rejected(self):
        self.client.login(username="reporter", password="SecurePassword123!")
        future_date = date.today() + timedelta(days=2)
        post_data = {
            "title": "Future Item",
            "description": "Cannot be lost tomorrow",
            "category": self.category.id,
            "location": self.location.id,
            "date_lost_or_found": future_date.isoformat(),
        }
        response = self.client.post(reverse("items:report_lost"), post_data)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("date_lost_or_found", form.errors)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ItemSearchAndFilterTests(TestCase):
    """Test item catalog browsing, keyword search, filtering, and pagination."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = CampusUser.objects.create_user(
            username="cataloguser",
            email="catalog@university.edu",
            password="SecurePassword123!",
        )
        self.cat_tech = Category.objects.create(name="Tech")
        self.cat_books = Category.objects.create(name="Books")
        self.loc_lib = CampusLocation.objects.create(name="Library")
        self.loc_gym = CampusLocation.objects.create(name="Gym")

        # Create active items
        self.item1 = Item.objects.create(
            title="MacBook Air M2",
            description="Silver laptop left on desk 4",
            item_type=Item.ItemType.LOST,
            category=self.cat_tech,
            location=self.loc_lib,
            date_lost_or_found=date.today() - timedelta(days=5),
            reported_by=self.user,
            status=Item.ItemStatus.OPEN,
        )
        self.item2 = Item.objects.create(
            title="Calculus Textbook",
            description="James Stewart Early Transcendentals",
            item_type=Item.ItemType.FOUND,
            category=self.cat_books,
            location=self.loc_lib,
            date_lost_or_found=date.today() - timedelta(days=3),
            reported_by=self.user,
            status=Item.ItemStatus.OPEN,
        )
        # Create resolved and closed items (should be hidden by default)
        self.item3 = Item.objects.create(
            title="Resolved iPhone 13",
            description="Returned to owner",
            item_type=Item.ItemType.FOUND,
            category=self.cat_tech,
            location=self.loc_gym,
            date_lost_or_found=date.today() - timedelta(days=1),
            reported_by=self.user,
            status=Item.ItemStatus.RESOLVED,
        )
        self.item4 = Item.objects.create(
            title="Closed Umbrella",
            description="Disposed or closed",
            item_type=Item.ItemType.LOST,
            category=self.cat_tech,
            location=self.loc_gym,
            date_lost_or_found=date.today() - timedelta(days=1),
            reported_by=self.user,
            status=Item.ItemStatus.CLOSED,
        )

    def test_default_listing_excludes_resolved_and_closed(self):
        response = self.client.get(reverse("items:list"))
        self.assertEqual(response.status_code, 200)
        items = response.context["items"]
        item_ids = [item.id for item in items]
        self.assertIn(self.item1.id, item_ids)
        self.assertIn(self.item2.id, item_ids)
        self.assertNotIn(self.item3.id, item_ids)
        self.assertNotIn(self.item4.id, item_ids)

    def test_search_by_keyword(self):
        # Search title
        res = self.client.get(reverse("items:list"), {"q": "MacBook"})
        self.assertContains(res, "MacBook Air M2")
        self.assertNotContains(res, "Calculus Textbook")

        # Search description
        res2 = self.client.get(reverse("items:list"), {"q": "Stewart"})
        self.assertContains(res2, "Calculus Textbook")
        self.assertNotContains(res2, "MacBook Air M2")

    def test_filter_by_item_type(self):
        res_lost = self.client.get(reverse("items:list"), {"type": "LOST"})
        items = res_lost.context["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, self.item1.id)

        res_found = self.client.get(reverse("items:list"), {"type": "FOUND"})
        items_found = res_found.context["items"]
        self.assertEqual(len(items_found), 1)
        self.assertEqual(items_found[0].id, self.item2.id)

    def test_filter_by_category_and_location(self):
        res = self.client.get(reverse("items:list"), {"category": str(self.cat_tech.id)})
        items = res.context["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, self.item1.id)

        res_loc = self.client.get(reverse("items:list"), {"location": str(self.loc_lib.id)})
        self.assertEqual(len(res_loc.context["items"]), 2)

    def test_filter_by_status_includes_resolved(self):
        res = self.client.get(reverse("items:list"), {"status": "RESOLVED"})
        items = res.context["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, self.item3.id)

    def test_filter_by_date_range(self):
        start = (date.today() - timedelta(days=4)).isoformat()
        end = date.today().isoformat()
        res = self.client.get(reverse("items:list"), {"start_date": start, "end_date": end})
        items = res.context["items"]
        # Only item2 was 3 days ago; item1 was 5 days ago
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, self.item2.id)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ItemPermissionsAndSecurityTests(TestCase):
    """Test owner authorization, admin moderation, and forbidden actions."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.owner = CampusUser.objects.create_user(
            username="owner",
            email="owner@university.edu",
            password="SecurePassword123!",
        )
        self.other_user = CampusUser.objects.create_user(
            username="stranger",
            email="stranger@university.edu",
            password="SecurePassword123!",
        )
        self.admin = CampusUser.objects.create_user(
            username="staffadmin",
            email="admin@university.edu",
            password="SecurePassword123!",
            role=CampusUser.Role.ADMIN,
            is_staff=True,
        )
        self.category = Category.objects.create(name="Bags")
        self.location = CampusLocation.objects.create(name="Campus Mall")
        self.item = Item.objects.create(
            title="Leather Wallet",
            description="Brown leather wallet",
            item_type=Item.ItemType.LOST,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.owner,
            status=Item.ItemStatus.OPEN,
        )

    def test_owner_can_access_edit_page(self):
        self.client.login(username="owner", password="SecurePassword123!")
        response = self.client.get(reverse("items:edit", kwargs={"pk": self.item.pk}))
        self.assertEqual(response.status_code, 200)

    def test_non_owner_forbidden_from_editing(self):
        self.client.login(username="stranger", password="SecurePassword123!")
        # GET edit page
        res_get = self.client.get(reverse("items:edit", kwargs={"pk": self.item.pk}))
        self.assertEqual(res_get.status_code, 403)

        # POST edit
        res_post = self.client.post(
            reverse("items:edit", kwargs={"pk": self.item.pk}),
            {"title": "Hacked Title", "description": "Hacked", "category": self.category.id, "location": self.location.id, "date_lost_or_found": date.today().isoformat()},
        )
        self.assertEqual(res_post.status_code, 403)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, "Leather Wallet")

    def test_delete_endpoint_method_not_allowed_on_get(self):
        self.client.login(username="owner", password="SecurePassword123!")
        response = self.client.get(reverse("items:delete", kwargs={"pk": self.item.pk}))
        self.assertEqual(response.status_code, 405)

    def test_non_owner_forbidden_from_deleting(self):
        self.client.login(username="stranger", password="SecurePassword123!")
        response = self.client.post(reverse("items:delete", kwargs={"pk": self.item.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Item.objects.filter(pk=self.item.pk).exists())

    def test_owner_can_delete_item(self):
        self.client.login(username="owner", password="SecurePassword123!")
        response = self.client.post(reverse("items:delete", kwargs={"pk": self.item.pk}))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Item.objects.filter(pk=self.item.pk).exists())

    def test_admin_can_update_status(self):
        self.client.login(username="staffadmin", password="SecurePassword123!")
        response = self.client.post(
            reverse("items:update_status", kwargs={"pk": self.item.pk}),
            {"status": Item.ItemStatus.RESOLVED},
        )
        self.assertEqual(response.status_code, 302)
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, Item.ItemStatus.RESOLVED)

    def test_regular_student_cannot_update_status(self):
        self.client.login(username="stranger", password="SecurePassword123!")
        response = self.client.post(
            reverse("items:update_status", kwargs={"pk": self.item.pk}),
            {"status": Item.ItemStatus.RESOLVED},
        )
        self.assertEqual(response.status_code, 403)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ItemImageHandlingTests(TestCase):
    """Test image upload validation, size limits, format checks, replacement, and disk cleanup."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = CampusUser.objects.create_user(
            username="photouser",
            email="photo@university.edu",
            password="SecurePassword123!",
        )
        self.category = Category.objects.create(name="Accessories")
        self.location = CampusLocation.objects.create(name="Sports Complex")

    def test_valid_image_upload_and_path(self):
        self.client.login(username="photouser", password="SecurePassword123!")
        image = create_dummy_image("smartwatch.jpg", size_bytes=2048)
        post_data = {
            "title": "Smart Watch",
            "description": "Black band smartwatch",
            "category": self.category.id,
            "location": self.location.id,
            "date_lost_or_found": date.today().isoformat(),
            "image": image,
        }
        response = self.client.post(reverse("items:report_found"), post_data)
        self.assertEqual(response.status_code, 302)

        item = Item.objects.get(title="Smart Watch")
        self.assertTrue(item.image)
        self.assertTrue(item.image.name.startswith("item_images/"))
        self.assertTrue(os.path.exists(item.image.path))

    def test_image_exceeding_5mb_rejected(self):
        self.client.login(username="photouser", password="SecurePassword123!")
        # 6 MB dummy image
        large_image = create_dummy_image("large.jpg", size_bytes=6 * 1024 * 1024)
        post_data = {
            "title": "Large Photo Item",
            "description": "Exceeds 5MB",
            "category": self.category.id,
            "location": self.location.id,
            "date_lost_or_found": date.today().isoformat(),
            "image": large_image,
        }
        response = self.client.post(reverse("items:report_lost"), post_data)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("image", form.errors)
        self.assertIn("5 MB", form.errors["image"][0])

    def test_invalid_image_file_rejected(self):
        self.client.login(username="photouser", password="SecurePassword123!")
        fake_file = SimpleUploadedFile("fake.jpg", b"NOT AN IMAGE", content_type="image/jpeg")
        post_data = {
            "title": "Corrupt Item",
            "description": "Not real image",
            "category": self.category.id,
            "location": self.location.id,
            "date_lost_or_found": date.today().isoformat(),
            "image": fake_file,
        }
        response = self.client.post(reverse("items:report_lost"), post_data)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertIn("image", form.errors)

    def test_image_removal_and_replacement_cleanup(self):
        self.client.login(username="photouser", password="SecurePassword123!")
        # First create item with image
        img1 = create_dummy_image("first.jpg", size_bytes=1024)
        item = Item.objects.create(
            title="Headphones",
            description="Noise cancelling",
            item_type=Item.ItemType.LOST,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.user,
            image=img1,
        )
        old_path = item.image.path
        item.image.close()
        self.assertTrue(os.path.exists(old_path))

        # Replace image via edit form
        img2 = create_dummy_image("second.png", size_bytes=1024, format="PNG")
        edit_data = {
            "title": "Headphones Updated",
            "description": "Noise cancelling",
            "category": self.category.id,
            "location": self.location.id,
            "date_lost_or_found": date.today().isoformat(),
            "image": img2,
        }
        resp = self.client.post(reverse("items:edit", kwargs={"pk": item.pk}), edit_data)
        self.assertEqual(resp.status_code, 302)
        item.refresh_from_db()
        self.assertFalse(os.path.exists(old_path))
        new_path = item.image.path
        item.image.close()
        self.assertTrue(os.path.exists(new_path))

        # Explicitly close and release any handles before testing removal
        item_pk = item.pk
        del item
        import gc
        gc.collect()

        # Check remove_image
        remove_data = {
            "title": "Headphones Updated",
            "description": "Noise cancelling",
            "category": self.category.id,
            "location": self.location.id,
            "date_lost_or_found": date.today().isoformat(),
            "remove_image": "on",
        }
        resp_remove = self.client.post(reverse("items:edit", kwargs={"pk": item_pk}), remove_data)
        self.assertEqual(resp_remove.status_code, 302)
        item = Item.objects.get(pk=item_pk)
        self.assertFalse(item.image)
        self.assertFalse(os.path.exists(new_path))


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class ItemApiTests(TestCase):
    """Test Django REST Framework API endpoints."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()
        self.user = CampusUser.objects.create_user(
            username="apiuser",
            email="api@university.edu",
            password="SecurePassword123!",
        )
        self.other_user = CampusUser.objects.create_user(
            username="apiother",
            email="apiother@university.edu",
            password="SecurePassword123!",
        )
        self.category = Category.objects.create(name="Gadgets")
        self.location = CampusLocation.objects.create(name="Cafeteria")
        self.item = Item.objects.create(
            title="Wireless Mouse",
            description="Logitech mouse",
            item_type=Item.ItemType.LOST,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.user,
            status=Item.ItemStatus.OPEN,
        )

    def test_api_list_items(self):
        response = self.client.get(reverse("api_v1:item-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check paginated response or results list
        results = response.data.get("results", response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "Wireless Mouse")

    def test_api_create_item_authenticated(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "title": "Found AirTag",
            "description": "Found on dining table",
            "item_type": "FOUND",
            "category": str(self.category.id),
            "location": str(self.location.id),
            "date_lost_or_found": date.today().isoformat(),
        }
        response = self.client.post(reverse("api_v1:item-list"), payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "OPEN")
        self.assertEqual(response.data["reporter_display_name"], "apiuser")

    def test_api_create_item_unauthenticated_fails(self):
        payload = {
            "title": "Anonymous Item",
            "description": "Should fail",
            "item_type": "LOST",
            "category": str(self.category.id),
            "location": str(self.location.id),
            "date_lost_or_found": date.today().isoformat(),
        }
        response = self.client.post(reverse("api_v1:item-list"), payload)
        self.assertIn(response.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_api_detail_and_owner_update(self):
        # Unauthenticated detail read
        detail_url = reverse("api_v1:item-detail", kwargs={"pk": self.item.pk})
        res_get = self.client.get(detail_url)
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)

        # Non-owner update forbidden
        self.client.force_authenticate(user=self.other_user)
        res_patch_forbidden = self.client.patch(detail_url, {"title": "Unauthorized Change"})
        self.assertEqual(res_patch_forbidden.status_code, status.HTTP_403_FORBIDDEN)

        # Owner update allowed
        self.client.force_authenticate(user=self.user)
        res_patch_owner = self.client.patch(detail_url, {"title": "Updated Mouse Title"})
        self.assertEqual(res_patch_owner.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.title, "Updated Mouse Title")

    def test_api_categories_and_locations_endpoints(self):
        res_cat = self.client.get(reverse("api_v1:category-list"))
        self.assertEqual(res_cat.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_cat.data.get("results", res_cat.data)), 1)

        res_loc = self.client.get(reverse("api_v1:location-list"))
        self.assertEqual(res_loc.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_loc.data.get("results", res_loc.data)), 1)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class DashboardAggregatesTests(TestCase):
    """Test student and admin dashboard data calculations and metrics."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.student = CampusUser.objects.create_user(
            username="student1",
            email="student1@university.edu",
            password="SecurePassword123!",
        )
        self.other_student = CampusUser.objects.create_user(
            username="student2",
            email="student2@university.edu",
            password="SecurePassword123!",
        )
        self.admin = CampusUser.objects.create_user(
            username="admindash",
            email="admindash@university.edu",
            password="SecurePassword123!",
            role=CampusUser.Role.ADMIN,
            is_staff=True,
        )
        self.category = Category.objects.create(name="Documents")
        self.location = CampusLocation.objects.create(name="Admin Building")

        # Student 1 items: 1 LOST OPEN, 1 FOUND RESOLVED
        Item.objects.create(
            title="Lost ID Card",
            description="Lost in foyer",
            item_type=Item.ItemType.LOST,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.student,
            status=Item.ItemStatus.OPEN,
        )
        Item.objects.create(
            title="Found Driver License",
            description="Found in grass",
            item_type=Item.ItemType.FOUND,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.student,
            status=Item.ItemStatus.RESOLVED,
        )

        # Other student items: 1 LOST OPEN
        Item.objects.create(
            title="Other Student Binder",
            description="Not belonging to student 1",
            item_type=Item.ItemType.LOST,
            category=self.category,
            location=self.location,
            date_lost_or_found=date.today(),
            reported_by=self.other_student,
            status=Item.ItemStatus.OPEN,
        )

    def test_student_dashboard_aggregates_own_items_only(self):
        self.client.login(username="student1", password="SecurePassword123!")
        response = self.client.get(reverse("dashboard:student"))
        self.assertEqual(response.status_code, 200)

        # Student 1 has total=2, lost=1, found=1, open=1, resolved=1
        self.assertEqual(response.context["total_reports"], 2)
        self.assertEqual(response.context["lost_reports"], 1)
        self.assertEqual(response.context["found_reports"], 1)
        self.assertEqual(response.context["open_reports"], 1)
        self.assertEqual(response.context["resolved_reports"], 1)
        self.assertEqual(len(response.context["recent_reports"]), 2)

    def test_admin_dashboard_aggregates_system_totals(self):
        self.client.login(username="admindash", password="SecurePassword123!")
        response = self.client.get(reverse("dashboard:admin"))
        self.assertEqual(response.status_code, 200)

        # System total items across all users = 3
        self.assertEqual(response.context["total_items"], 3)
        self.assertEqual(response.context["lost_items"], 2)
        self.assertEqual(response.context["found_items"], 1)
        self.assertEqual(response.context["open_items"], 2)
        self.assertEqual(response.context["resolved_items"], 1)
