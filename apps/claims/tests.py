"""Comprehensive test suite for Phase 4 Ownership Claims & Verification."""
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import CampusUser
from apps.claims.forms import ClaimReviewForm, ClaimSubmissionForm
from apps.claims.models import Claim, ClaimStatus
from apps.claims.services import (
    approve_claim,
    mark_claim_under_review,
    reject_claim,
    submit_claim,
    withdraw_claim,
)
from apps.items.models import CampusLocation, Category, Item
from apps.matching.models import MatchStatus, PotentialMatch
from apps.notifications.models import Notification, NotificationType


class ClaimsTestBase(TestCase):
    """Base setup fixture with campus locations, categories, and users."""

    def setUp(self):
        self.location = CampusLocation.objects.create(
            name="Library Study Room 204", description="Room 204"
        )
        self.category = Category.objects.create(
            name="Electronics", description="Electronic devices"
        )

        self.admin = CampusUser.objects.create_user(
            username="campus_admin",
            email="admin@university.edu",
            password="AdminPassword123!",
            role=CampusUser.Role.ADMIN,
            is_staff=True,
        )
        self.finder = CampusUser.objects.create_user(
            username="finder_jane",
            email="jane@university.edu",
            password="TestPassword123!",
            role=CampusUser.Role.STUDENT,
        )
        self.student_a = CampusUser.objects.create_user(
            username="claimant_alice",
            email="alice@university.edu",
            password="TestPassword123!",
            role=CampusUser.Role.STUDENT,
            student_id="STU-001",
        )
        self.student_b = CampusUser.objects.create_user(
            username="claimant_bob",
            email="bob@university.edu",
            password="TestPassword123!",
            role=CampusUser.Role.STUDENT,
            student_id="STU-002",
        )

        # Found item turned into campus desk
        self.found_item = Item.objects.create(
            title="Black Dell XPS Laptop",
            description="Found in Study Room 204 with silver stickers.",
            item_type=Item.ItemType.FOUND,
            category=self.category,
            location=self.location,
            reported_by=self.finder,
            status=Item.ItemStatus.OPEN,
            date_lost_or_found=timezone.now().date(),
        )


class ClaimModelValidationTests(ClaimsTestBase):
    """Test model-level constraints and clean validations."""

    def test_reporter_cannot_claim_own_item(self):
        claim = Claim(
            claimant=self.finder,
            item=self.found_item,
            claim_description="Trying to claim my own report.",
            distinguishing_features="Scratch on bottom plate and logo sticker.",
        )
        with self.assertRaises(ValidationError) as ctx:
            claim.clean()
        self.assertIn("cannot submit an ownership claim for an item you reported", str(ctx.exception))

    def test_cannot_claim_resolved_item(self):
        self.found_item.status = Item.ItemStatus.RESOLVED
        self.found_item.save()

        claim = Claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Claiming already resolved item.",
            distinguishing_features="Scratch on bottom plate and logo sticker.",
        )
        with self.assertRaises(ValidationError) as ctx:
            claim.clean()
        self.assertIn("can no longer be claimed", str(ctx.exception))

    def test_unique_active_claim_constraint(self):
        # Alice submits first active claim
        Claim.objects.create(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="First active claim.",
            distinguishing_features="Scratch on bottom plate and logo sticker.",
            status=ClaimStatus.PENDING,
        )
        # Attempting second active claim from Alice should fail integrity/validation
        duplicate_claim = Claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Duplicate active claim.",
            distinguishing_features="Scratch on bottom plate and logo sticker.",
            status=ClaimStatus.PENDING,
        )
        with self.assertRaises(ValidationError):
            duplicate_claim.clean()


class ClaimServiceLayerTests(ClaimsTestBase):
    """Test the domain service workflows and state transitions."""

    def test_submit_claim_workflow(self):
        claim = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="I lost this laptop during study group.",
            distinguishing_features="Small dent on corner and custom Linux sticker.",
            item_contents="Includes 65W USB-C charger and wireless mouse.",
            last_seen_details="Study Room 204 at 4 PM.",
        )
        self.assertEqual(claim.status, ClaimStatus.PENDING)
        self.found_item.refresh_from_db()
        self.assertEqual(self.found_item.status, Item.ItemStatus.CLAIM_PENDING)

        # Verify confirmation notification created for claimant
        student_notif = Notification.objects.filter(
            recipient=self.student_a, notification_type=NotificationType.CLAIM_SUBMITTED
        )
        self.assertTrue(student_notif.exists())

    def test_submit_claim_with_potential_match(self):
        lost_item = Item.objects.create(
            title="Lost Dell XPS Laptop",
            description="Silver stickers, lost in library.",
            item_type=Item.ItemType.LOST,
            category=self.category,
            location=self.location,
            reported_by=self.student_a,
            date_lost_or_found=timezone.now().date(),
        )
        # Retrieve or create potential match (may be auto-generated by signal)
        match, _ = PotentialMatch.objects.get_or_create(
            lost_item=lost_item,
            found_item=self.found_item,
            defaults={"similarity_score": 0.88, "status": MatchStatus.SUGGESTED},
        )

        claim = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            potential_match=match,
            claim_description="Initiated through AI match engine.",
            distinguishing_features="Custom sticker and distinctive scratch.",
        )
        match.refresh_from_db()
        self.assertEqual(match.status, MatchStatus.CLAIMED)
        self.assertEqual(claim.potential_match, match)

    def test_admin_under_review_transition(self):
        claim = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Valid claim under review.",
            distinguishing_features="Serial number ends with 4920.",
        )
        mark_claim_under_review(claim, self.admin, admin_notes="Checking serial with physical asset.")
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.UNDER_REVIEW)
        self.assertEqual(claim.reviewed_by, self.admin)
        self.assertIn("Checking serial", claim.admin_notes)

    def test_admin_approval_resolves_item_and_rejects_competing_claims(self):
        # Alice files claim 1
        claim_alice = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Alice's claim.",
            distinguishing_features="Verified serial number ends in 4920.",
        )
        # Bob files competing claim 2
        claim_bob = submit_claim(
            claimant=self.student_b,
            item=self.found_item,
            claim_description="Bob's competing claim.",
            distinguishing_features="Black laptop with general markings.",
        )

        # Admin approves Alice's claim
        approve_claim(claim_alice, self.admin, admin_notes="Alice's serial verified.")

        claim_alice.refresh_from_db()
        self.assertEqual(claim_alice.status, ClaimStatus.APPROVED)
        self.assertIsNotNone(claim_alice.resolved_at)

        self.found_item.refresh_from_db()
        self.assertEqual(self.found_item.status, Item.ItemStatus.RESOLVED)

        # Bob's claim must be auto-rejected with informative rejection reason
        claim_bob.refresh_from_db()
        self.assertEqual(claim_bob.status, ClaimStatus.REJECTED)
        self.assertIn("verified and approved by campus administration", claim_bob.rejection_reason)

        # Check notifications
        alice_notif = Notification.objects.filter(
            recipient=self.student_a, notification_type=NotificationType.CLAIM_APPROVED
        )
        self.assertTrue(alice_notif.exists())

        bob_notif = Notification.objects.filter(
            recipient=self.student_b, notification_type=NotificationType.CLAIM_REJECTED
        )
        self.assertTrue(bob_notif.exists())

    def test_admin_rejection_reverts_item_to_open_when_no_active_claims(self):
        claim = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Invalid claim.",
            distinguishing_features="Incorrect serial number provided.",
        )
        self.found_item.refresh_from_db()
        self.assertEqual(self.found_item.status, Item.ItemStatus.CLAIM_PENDING)

        reject_claim(
            claim,
            self.admin,
            rejection_reason="Serial number did not match hardware inspection.",
            admin_notes="Device serial inspected.",
        )
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.REJECTED)
        self.assertEqual(claim.rejection_reason, "Serial number did not match hardware inspection.")

        # With no other active claims, item reverts to OPEN
        self.found_item.refresh_from_db()
        self.assertEqual(self.found_item.status, Item.ItemStatus.OPEN)

    def test_claimant_withdrawal_reverts_item_to_open(self):
        claim = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Accidental submission.",
            distinguishing_features="Realized this was not my laptop.",
        )
        withdraw_claim(claim, self.student_a)
        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.WITHDRAWN)

        self.found_item.refresh_from_db()
        self.assertEqual(self.found_item.status, Item.ItemStatus.OPEN)


class ClaimViewAndAccessControlTests(ClaimsTestBase):
    """Test HTTP views, access controls, forms, and permission boundaries."""

    def test_claim_submission_requires_login(self):
        url = reverse("claims:submit", kwargs={"item_id": self.found_item.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_claim_submission_view_renders_and_submits(self):
        self.client.login(username="claimant_alice", password="TestPassword123!")
        url = reverse("claims:submit", kwargs={"item_id": self.found_item.id})
        get_response = self.client.get(url)
        self.assertEqual(get_response.status_code, 200)
        self.assertContains(get_response, "Submit Ownership Claim")

        post_data = {
            "claim_description": "Left my laptop in the study room.",
            "distinguishing_features": "Dell XPS 13 with custom Linux sticker on top cover.",
            "item_contents": "Includes charger and mouse.",
            "last_seen_details": "4:00 PM yesterday.",
        }
        post_response = self.client.post(url, post_data)
        self.assertEqual(post_response.status_code, 302)

        # Verify claim exists in database
        self.assertTrue(Claim.objects.filter(claimant=self.student_a, item=self.found_item).exists())

    def test_student_cannot_view_other_student_claim_details(self):
        claim = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Alice's private claim.",
            distinguishing_features="Alice's private password hint.",
        )
        # Bob logs in and tries to access Alice's claim detail
        self.client.login(username="claimant_bob", password="TestPassword123!")
        url = reverse("claims:detail", kwargs={"claim_id": claim.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_staff_admin_can_view_student_claim_details(self):
        claim = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Alice submitted claim.",
            distinguishing_features="Alice verified serial number 99482.",
        )
        self.client.login(username="campus_admin", password="AdminPassword123!")
        url = reverse("claims:detail", kwargs={"claim_id": claim.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice verified serial number 99482.")

    def test_student_cannot_access_admin_dashboard_or_review(self):
        claim = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Alice's claim.",
            distinguishing_features="Alice's confidential evidence.",
        )
        self.client.login(username="claimant_alice", password="TestPassword123!")

        # Admin queue
        resp_queue = self.client.get(reverse("claims:admin_dashboard"))
        self.assertEqual(resp_queue.status_code, 403)

        # Admin review
        resp_review = self.client.get(reverse("claims:admin_review", kwargs={"claim_id": claim.id}))
        self.assertEqual(resp_review.status_code, 403)

    def test_admin_claim_review_post_approval(self):
        claim = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Alice's claim.",
            distinguishing_features="Serial number 12345 verified.",
        )
        self.client.login(username="campus_admin", password="AdminPassword123!")
        url = reverse("claims:admin_review", kwargs={"claim_id": claim.id})

        post_data = {
            "action": "approve",
            "admin_notes": "Serial verified at desk.",
            "rejection_reason": "",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        claim.refresh_from_db()
        self.assertEqual(claim.status, ClaimStatus.APPROVED)
        self.found_item.refresh_from_db()
        self.assertEqual(self.found_item.status, Item.ItemStatus.RESOLVED)

    def test_admin_claim_review_post_rejection_requires_reason(self):
        claim = submit_claim(
            claimant=self.student_a,
            item=self.found_item,
            claim_description="Alice's claim.",
            distinguishing_features="Serial number 12345 verified.",
        )
        self.client.login(username="campus_admin", password="AdminPassword123!")
        url = reverse("claims:admin_review", kwargs={"claim_id": claim.id})

        # Rejecting with empty rejection_reason should be rejected by form validation
        post_data = {
            "action": "reject",
            "admin_notes": "Serial did not match.",
            "rejection_reason": "",
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A rejection reason must be provided")


class DemoDataManagementCommandTests(TestCase):
    """Test the showcase seed demo data management command."""

    def test_seed_claim_demo_data_command(self):
        call_command("seed_claim_demo_data")
        # Verify 3 claims exist in approved, rejected, and pending states
        self.assertTrue(Claim.objects.filter(status=ClaimStatus.APPROVED).exists())
        self.assertTrue(Claim.objects.filter(status=ClaimStatus.REJECTED).exists())
        self.assertTrue(Claim.objects.filter(status=ClaimStatus.PENDING).exists())

        # Test idempotency by running a second time
        call_command("seed_claim_demo_data")
        self.assertEqual(Claim.objects.filter(status=ClaimStatus.APPROVED).count(), 1)
