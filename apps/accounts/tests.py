"""Comprehensive automated tests for accounts app: registration, authentication,
role-based permissions, profile management, throttling, and administrator provisioning.
"""
import io
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.test import TestCase, override_settings
from django.urls import reverse

CampusUser = get_user_model()


class StudentRegistrationTests(TestCase):
    """Test student registration constraints and workflows."""

    def setUp(self):
        cache.clear()
        self.register_url = reverse("accounts:register")
        self.login_url = reverse("accounts:login")

    def test_registration_view_renders(self):
        """GET request loads the student registration page."""
        response = self.client.get(self.register_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Registration")
        self.assertContains(response, "University Email Required")

    def test_successful_student_registration(self):
        """Valid submission creates a STUDENT account with hashed password."""
        payload = {
            "first_name": "Jane",
            "last_name": "Doe",
            "email": "jane.doe@university.edu",
            "student_id": "STU-2026-0001",
            "phone_number": "+1234567890",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        }
        response = self.client.post(self.register_url, data=payload)
        self.assertRedirects(response, self.login_url)

        user = CampusUser.objects.get(email="jane.doe@university.edu")
        self.assertEqual(user.first_name, "Jane")
        self.assertEqual(user.last_name, "Doe")
        self.assertEqual(user.student_id, "STU-2026-0001")
        self.assertEqual(user.role, CampusUser.Role.STUDENT)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_email_verified)
        self.assertTrue(user.check_password("SecurePassword123!"))

    @override_settings(UNIVERSITY_EMAIL_DOMAINS=["university.edu", "campus.ac.in"])
    def test_registration_enforces_approved_university_domain(self):
        """Rejects registration with unapproved email domains."""
        payload = {
            "first_name": "External",
            "last_name": "User",
            "email": "external.user@gmail.com",
            "student_id": "STU-EXT-9999",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        }
        response = self.client.post(self.register_url, data=payload)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(
            form,
            "email",
            "Registration is restricted to university email domains (university.edu, campus.ac.in).",
        )
        self.assertFalse(CampusUser.objects.filter(email="external.user@gmail.com").exists())

    def test_registration_rejects_duplicate_email(self):
        """Rejects registration with an email that is already registered."""
        CampusUser.objects.create_user(
            username="existing@university.edu",
            email="existing@university.edu",
            password="ExistingPassword123!",
            role=CampusUser.Role.STUDENT,
        )
        payload = {
            "first_name": "Duplicate",
            "last_name": "Person",
            "email": "EXISTING@UNIVERSITY.EDU",  # Test case-insensitivity
            "student_id": "STU-NEW-8888",
            "password": "SecurePassword123!",
            "confirm_password": "SecurePassword123!",
        }
        response = self.client.post(self.register_url, data=payload)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(
            form,
            "email",
            "An account with this university email address already exists.",
        )

    def test_registration_rejects_duplicate_student_id(self):
        """Rejects registration with an already registered student_id."""
        CampusUser.objects.create_user(
            username="student1@university.edu",
            email="student1@university.edu",
            student_id="STU-DUPLICATE-01",
            password="Password123!",
            role=CampusUser.Role.STUDENT,
        )
        payload = {
            "first_name": "Second",
            "last_name": "Student",
            "email": "student2@university.edu",
            "student_id": "STU-DUPLICATE-01",
            "password": "Password123!",
            "confirm_password": "Password123!",
        }
        response = self.client.post(self.register_url, data=payload)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(
            form,
            "student_id",
            "A student with this registration number has already registered.",
        )

    def test_registration_rejects_mismatched_passwords(self):
        """Rejects registration when password and confirmation do not match."""
        payload = {
            "first_name": "Mismatch",
            "last_name": "Test",
            "email": "mismatch@university.edu",
            "student_id": "STU-MIS-0001",
            "password": "Password123!",
            "confirm_password": "CompletelyDifferent456!",
        }
        response = self.client.post(self.register_url, data=payload)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(form, "confirm_password", "Passwords do not match.")

    def test_authenticated_user_redirected_from_register(self):
        """Logged-in users visiting the registration page are redirected to home."""
        user = CampusUser.objects.create_user(
            username="logged@university.edu",
            email="logged@university.edu",
            password="Password123!",
            role=CampusUser.Role.STUDENT,
        )
        self.client.force_login(user)
        response = self.client.get(self.register_url)
        self.assertRedirects(response, reverse("home"))


class AuthenticationTests(TestCase):
    """Test login, logout, and brute-force throttling behaviors."""

    def setUp(self):
        cache.clear()
        self.login_url = reverse("accounts:login")
        self.logout_url = reverse("accounts:logout")
        self.student = CampusUser.objects.create_user(
            username="alice@university.edu",
            email="alice@university.edu",
            password="ValidPassword123!",
            first_name="Alice",
            last_name="Smith",
            role=CampusUser.Role.STUDENT,
        )

    def test_login_view_renders(self):
        """GET request loads the sign-in form."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Campus Sign In")

    def test_login_successful_with_email(self):
        """Users can log in using their case-insensitive university email."""
        response = self.client.post(
            self.login_url,
            data={"email": "ALICE@UNIVERSITY.EDU", "password": "ValidPassword123!"},
        )
        self.assertRedirects(response, reverse("dashboard:student"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.student.pk)

    def test_login_invalid_credentials_shows_error(self):
        """Failed authentication displays appropriate error message."""
        response = self.client.post(
            self.login_url,
            data={"email": "alice@university.edu", "password": "WrongPassword!"},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(
            form,
            None,
            "Invalid email/username or password. Please verify your credentials.",
        )

    def test_login_inactive_user_rejected(self):
        """Deactivated accounts cannot authenticate."""
        self.student.is_active = False
        self.student.save()
        response = self.client.post(
            self.login_url,
            data={"email": "alice@university.edu", "password": "ValidPassword123!"},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(
            form,
            None,
            "This account has been deactivated. Please contact campus security.",
        )

    def test_brute_force_throttling_lockout(self):
        """After 5 consecutive failures, authentication is temporarily locked out."""
        for _ in range(5):
            self.client.post(
                self.login_url,
                data={"email": "alice@university.edu", "password": "WrongPassword!"},
            )

        # 6th attempt should be blocked by rate limiting
        response = self.client.post(
            self.login_url,
            data={"email": "alice@university.edu", "password": "ValidPassword123!"},
        )
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertFormError(
            form,
            None,
            "Too many failed login attempts. For security reasons, please wait 15 minutes before trying again.",
        )

    def test_logout_via_post_terminates_session(self):
        """POST to logout clears user session and redirects to home."""
        self.client.force_login(self.student)
        self.assertTrue("_auth_user_id" in self.client.session)

        response = self.client.post(self.logout_url)
        self.assertRedirects(response, reverse("home"))
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_logout_via_get_redirects_safely(self):
        """GET to logout redirects to home without throwing 405."""
        self.client.force_login(self.student)
        response = self.client.get(self.logout_url)
        self.assertRedirects(response, reverse("home"))


class RoleRedirectionAndPermissionsTests(TestCase):
    """Test role dispatcher and role-based access restrictions."""

    def setUp(self):
        cache.clear()
        self.student = CampusUser.objects.create_user(
            username="student@university.edu",
            email="student@university.edu",
            password="Password123!",
            role=CampusUser.Role.STUDENT,
        )
        self.admin = CampusUser.objects.create_user(
            username="admin@university.edu",
            email="admin@university.edu",
            password="Password123!",
            role=CampusUser.Role.ADMIN,
        )
        self.super_admin = CampusUser.objects.create_user(
            username="super@university.edu",
            email="super@university.edu",
            password="Password123!",
            role=CampusUser.Role.SUPER_ADMIN,
        )

    def test_dashboard_dispatcher_routes_correctly(self):
        """Dashboard index redirects to role-specific dashboard views."""
        # Anonymous redirects to login
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, reverse("accounts:login"))

        # Student redirects to student dashboard
        self.client.force_login(self.student)
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, reverse("dashboard:student"))

        # Admin redirects to admin dashboard
        self.client.force_login(self.admin)
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, reverse("dashboard:admin"))

        # Super Admin redirects to super admin dashboard
        self.client.force_login(self.super_admin)
        response = self.client.get(reverse("dashboard:index"))
        self.assertRedirects(response, reverse("dashboard:super_admin"))

    def test_student_forbidden_from_admin_areas(self):
        """Students receive 403 Forbidden when attempting to access staff or super admin views."""
        self.client.force_login(self.student)
        
        response = self.client.get(reverse("dashboard:admin"))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse("dashboard:super_admin"))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse("accounts:create_admin"))
        self.assertEqual(response.status_code, 403)

    def test_admin_forbidden_from_super_admin_views(self):
        """Staff administrators receive 403 Forbidden for super admin only pages."""
        self.client.force_login(self.admin)

        response = self.client.get(reverse("dashboard:super_admin"))
        self.assertEqual(response.status_code, 403)

        response = self.client.get(reverse("accounts:create_admin"))
        self.assertEqual(response.status_code, 403)


class ProfileTests(TestCase):
    """Test user profile display and update constraints."""

    def setUp(self):
        self.profile_url = reverse("accounts:profile")
        self.user = CampusUser.objects.create_user(
            username="profile.user@university.edu",
            email="profile.user@university.edu",
            student_id="STU-PROF-101",
            first_name="InitialFirst",
            last_name="InitialLast",
            phone_number="+1111111111",
            password="Password123!",
            role=CampusUser.Role.STUDENT,
        )

    def test_profile_requires_login(self):
        """Unauthenticated requests redirect to login."""
        response = self.client.get(self.profile_url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.profile_url}")

    def test_profile_view_renders_user_data(self):
        """Authenticated profile view displays current user information."""
        self.client.force_login(self.user)
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "InitialFirst")
        self.assertContains(response, "STU-PROF-101")
        self.assertContains(response, "profile.user@university.edu")

    def test_profile_update_allowed_fields(self):
        """User can update first_name, last_name, and phone_number."""
        self.client.force_login(self.user)
        payload = {
            "first_name": "UpdatedFirst",
            "last_name": "UpdatedLast",
            "phone_number": "+9999999999",
        }
        response = self.client.post(self.profile_url, data=payload)
        self.assertRedirects(response, self.profile_url)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "UpdatedFirst")
        self.assertEqual(self.user.last_name, "UpdatedLast")
        self.assertEqual(self.user.phone_number, "+9999999999")

    def test_profile_update_protects_sensitive_fields_against_tampering(self):
        """Malicious payload cannot modify role, email, student_id, or is_email_verified."""
        self.client.force_login(self.user)
        payload = {
            "first_name": "TamperFirst",
            "last_name": "TamperLast",
            "phone_number": "+1234567890",
            # Attempted parameter injection
            "role": "SUPER_ADMIN",
            "email": "hacked@university.edu",
            "student_id": "STU-HACKED",
            "is_email_verified": True,
            "is_staff": True,
            "is_superuser": True,
        }
        response = self.client.post(self.profile_url, data=payload)
        self.assertRedirects(response, self.profile_url)

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "TamperFirst")
        # Ensure protected fields were untouched
        self.assertEqual(self.user.role, CampusUser.Role.STUDENT)
        self.assertEqual(self.user.email, "profile.user@university.edu")
        self.assertEqual(self.user.student_id, "STU-PROF-101")
        self.assertFalse(self.user.is_email_verified)
        self.assertFalse(self.user.is_staff)
        self.assertFalse(self.user.is_superuser)

    def test_profile_picture_upload_valid_image(self):
        """Valid image upload updates user avatar."""
        self.client.force_login(self.user)

        # Generate small in-memory JPEG
        image_bytes = io.BytesIO()
        image = Image.new("RGB", (100, 100), color="blue")
        image.save(image_bytes, format="JPEG")
        image_bytes.seek(0)

        uploaded_file = SimpleUploadedFile("avatar.jpg", image_bytes.read(), content_type="image/jpeg")

        payload = {
            "first_name": "PhotoFirst",
            "last_name": "PhotoLast",
            "profile_picture": uploaded_file,
        }
        response = self.client.post(self.profile_url, data=payload)
        self.assertRedirects(response, self.profile_url)

        self.user.refresh_from_db()
        self.assertTrue(bool(self.user.profile_picture))


class AdminProvisioningTests(TestCase):
    """Test Super Admin administrative account provisioning."""

    def setUp(self):
        cache.clear()
        self.provision_url = reverse("accounts:create_admin")
        self.super_admin = CampusUser.objects.create_user(
            username="superadmin@university.edu",
            email="superadmin@university.edu",
            password="SuperPassword123!",
            role=CampusUser.Role.SUPER_ADMIN,
        )

    def test_super_admin_provisions_staff_admin(self):
        """Super Admin can provision an ADMIN account with staff privileges."""
        self.client.force_login(self.super_admin)
        payload = {
            "first_name": "Desk",
            "last_name": "Officer",
            "email": "desk.officer@university.edu",
            "phone_number": "+1122334455",
            "password": "StaffPassword123!",
            "confirm_password": "StaffPassword123!",
        }
        response = self.client.post(self.provision_url, data=payload)
        self.assertRedirects(response, self.provision_url)

        admin_user = CampusUser.objects.get(email="desk.officer@university.edu")
        self.assertEqual(admin_user.role, CampusUser.Role.ADMIN)
        self.assertTrue(admin_user.is_staff)
        self.assertFalse(admin_user.is_superuser)
        self.assertTrue(admin_user.check_password("StaffPassword123!"))


class AssignSuperAdminCommandTests(TestCase):
    """Test the assign_super_admin management command."""

    def setUp(self):
        self.student = CampusUser.objects.create_user(
            username="student_to_promote",
            email="promoteme@university.edu",
            password="SecurePassword123!",
            role=CampusUser.Role.STUDENT,
        )

    def test_assign_super_admin_by_email(self):
        out = io.StringIO()
        call_command("assign_super_admin", "promoteme@university.edu", noinput=True, stdout=out)
        self.assertIn("Successfully elevated", out.getvalue())
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, CampusUser.Role.SUPER_ADMIN)
        self.assertTrue(self.student.is_staff)
        self.assertTrue(self.student.is_superuser)
        self.assertTrue(self.student.is_super_admin)

    def test_assign_super_admin_by_username(self):
        out = io.StringIO()
        call_command("assign_super_admin", "student_to_promote", noinput=True, stdout=out)
        self.assertIn("Successfully elevated", out.getvalue())
        self.student.refresh_from_db()
        self.assertEqual(self.student.role, CampusUser.Role.SUPER_ADMIN)

    def test_assign_super_admin_nonexistent_user_fails(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("assign_super_admin", "nonexistent@university.edu", noinput=True)
        self.assertIn("No CampusUser account found", str(ctx.exception))

    def test_assign_super_admin_already_super_admin(self):
        self.student.role = CampusUser.Role.SUPER_ADMIN
        self.student.is_staff = True
        self.student.is_superuser = True
        self.student.save()

        out = io.StringIO()
        call_command("assign_super_admin", self.student.email, noinput=True, stdout=out)
        self.assertIn("is already a configured Super Administrator", out.getvalue())
