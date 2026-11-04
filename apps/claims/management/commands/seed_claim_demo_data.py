"""Management command to seed showcase demo data for Phase 4 Ownership Claims & Verification."""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CampusUser
from apps.claims.models import Claim, ClaimStatus
from apps.items.models import CampusLocation, Category, Item
from apps.notifications.models import Notification, NotificationType


class Command(BaseCommand):
    help = "Seeds idempotent demo data demonstrating the Phase 4 Ownership Verification lifecycle."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Phase 4 Claims & Ownership Verification demo data..."))

        # 1. Base Taxonomy
        category_elec, _ = Category.objects.get_or_create(
            name="Electronics",
            defaults={"description": "Mobile devices, laptops, headphones, chargers."},
        )
        category_acc, _ = Category.objects.get_or_create(
            name="Accessories",
            defaults={"description": "Watches, jewelry, sunglasses, bags."},
        )

        loc_lib, _ = CampusLocation.objects.get_or_create(
            name="Central Library — 2nd Floor Study Commons",
            defaults={"description": "Library building 2nd floor study commons and carrels."},
        )
        loc_union, _ = CampusLocation.objects.get_or_create(
            name="Student Union — Food Court & Lounge",
            defaults={"description": "Student Union 1st floor food court and casual seating lounge."},
        )

        # 2. Staff & Student Users
        admin_user, _ = CampusUser.objects.get_or_create(
            email="moderator@university.edu",
            defaults={
                "username": "desk_moderator",
                "first_name": "Marcus",
                "last_name": "Vance",
                "role": CampusUser.Role.ADMIN,
                "is_staff": True,
            },
        )
        admin_user.set_password("AdminPass123!")
        admin_user.is_staff = True
        admin_user.save()

        finder_user, _ = CampusUser.objects.get_or_create(
            email="sam_finder@university.edu",
            defaults={
                "username": "sam_finder",
                "first_name": "Samantha",
                "last_name": "Ray",
                "role": CampusUser.Role.STUDENT,
                "student_id": "STU-88201",
            },
        )
        finder_user.set_password("StudentPass123!")
        finder_user.save()

        alice, _ = CampusUser.objects.get_or_create(
            email="alice@university.edu",
            defaults={
                "username": "alice_chen",
                "first_name": "Alice",
                "last_name": "Chen",
                "role": CampusUser.Role.STUDENT,
                "student_id": "STU-94021",
                "phone_number": "+1-555-0142",
            },
        )
        alice.set_password("StudentPass123!")
        alice.save()

        bob, _ = CampusUser.objects.get_or_create(
            email="bob@university.edu",
            defaults={
                "username": "bob_miller",
                "first_name": "Bob",
                "last_name": "Miller",
                "role": CampusUser.Role.STUDENT,
                "student_id": "STU-77319",
                "phone_number": "+1-555-0189",
            },
        )
        bob.set_password("StudentPass123!")
        bob.save()

        charlie, _ = CampusUser.objects.get_or_create(
            email="charlie@university.edu",
            defaults={
                "username": "charlie_davis",
                "first_name": "Charlie",
                "last_name": "Davis",
                "role": CampusUser.Role.STUDENT,
                "student_id": "STU-65203",
                "phone_number": "+1-555-0164",
            },
        )
        charlie.set_password("StudentPass123!")
        charlie.save()

        # 3. Found Catalog Items
        # Item 1: Sony Headphones (Target of Alice's Approved claim and Bob's Rejected claim)
        sony_item, created_sony = Item.objects.get_or_create(
            title="Found Sony WH-1000XM5 Headphones",
            reported_by=finder_user,
            defaults={
                "description": "Black Sony wireless noise-cancelling headphones found on a table in the library 2nd floor study area.",
                "item_type": Item.ItemType.FOUND,
                "category": category_elec,
                "location": loc_lib,
                "status": Item.ItemStatus.CLAIM_PENDING,
                "date_lost_or_found": timezone.now().date(),
            },
        )
        if not created_sony and sony_item.status == Item.ItemStatus.RESOLVED:
            # Temporarily allow claim inspection if already resolved
            sony_item.status = Item.ItemStatus.CLAIM_PENDING
            sony_item.save(update_fields=["status"])

        # Item 2: Apple Watch (Target of Charlie's Pending claim)
        watch_item, created_watch = Item.objects.get_or_create(
            title="Found Apple Watch Series 9",
            reported_by=finder_user,
            defaults={
                "description": "Midnight aluminum Apple Watch with black magnetic loop band left near the Student Union lounge sofas.",
                "item_type": Item.ItemType.FOUND,
                "category": category_acc,
                "location": loc_union,
                "status": Item.ItemStatus.CLAIM_PENDING,
                "date_lost_or_found": timezone.now().date(),
            },
        )
        if not created_watch:
            watch_item.status = Item.ItemStatus.CLAIM_PENDING
            watch_item.save(update_fields=["status"])

        # 4. Claims Seed Data
        # Claim 1: Alice's Approved Claim
        alice_claim, created_ac = Claim.objects.get_or_create(
            claimant=alice,
            item=sony_item,
            defaults={
                "claim_description": (
                    "I was studying for my CS midterm in carrel #12 from 2:00 PM to 4:30 PM on Tuesday. "
                    "I packed up quickly when the fire alarm tested and accidentally left the case under the desk divider."
                ),
                "distinguishing_features": (
                    "Tiny 2mm metallic scratch on the left ear-cup slider near the hinge; customized dark neon-green "
                    "silicone ear pad covers. The serial number ends in 8941."
                ),
                "item_contents": "Includes original black hardshell case, braided 3.5mm coiled auxiliary jack, and dual-prong airline adapter.",
                "last_seen_details": "Central Library 2nd floor study commons, carrel #12 at 4:30 PM.",
                "status": ClaimStatus.APPROVED,
                "reviewed_by": admin_user,
                "resolved_at": timezone.now(),
                "admin_notes": "Serial number (ends in 8941) and green custom silicone pads verified against physical item at desk. Verified claimant identity with STU-94021.",
            },
        )
        if not created_ac:
            alice_claim.status = ClaimStatus.APPROVED
            alice_claim.reviewed_by = admin_user
            alice_claim.resolved_at = timezone.now()
            alice_claim.save()

        # Claim 2: Bob's Rejected Competing Claim on Sony Headphones
        bob_claim, created_bc = Claim.objects.get_or_create(
            claimant=bob,
            item=sony_item,
            defaults={
                "claim_description": "I think I dropped my headphones somewhere in the library yesterday afternoon.",
                "distinguishing_features": "Standard black Sony headphones, no special marks or stickers.",
                "item_contents": "Just the headphones, no case.",
                "last_seen_details": "Library around 3 PM.",
                "status": ClaimStatus.REJECTED,
                "reviewed_by": admin_user,
                "resolved_at": timezone.now(),
                "admin_notes": "Claimant provided no distinguishing features matching device. Device was found inside full case with serial ending in 8941.",
                "rejection_reason": "Distinctive markings and contents do not match the physical inventory item recovered. Ownership verified and released to another claimant.",
            },
        )
        if not created_bc:
            bob_claim.status = ClaimStatus.REJECTED
            bob_claim.reviewed_by = admin_user
            bob_claim.resolved_at = timezone.now()
            bob_claim.save()

        # Finalize Sony item to RESOLVED now that Alice's claim is APPROVED
        sony_item.status = Item.ItemStatus.RESOLVED
        sony_item.save(update_fields=["status"])

        # Claim 3: Charlie's Pending Review Claim on Apple Watch
        charlie_claim, created_cc = Claim.objects.get_or_create(
            claimant=charlie,
            item=watch_item,
            defaults={
                "claim_description": (
                    "I was working on group project notes in the Student Union food court and took off my watch while charging my phone. "
                    "Noticed it missing about 30 minutes later."
                ),
                "distinguishing_features": (
                    "Series 9, 45mm Midnight aluminum case with an aftermarket stainless steel Milanese magnetic loop. "
                    "Lockscreen passcode wallpaper is an orange geometric cat avatar."
                ),
                "item_contents": "Watch with magnetic Milanese band attached.",
                "last_seen_details": "Student Union Food Court high-top table #4, around 1:15 PM.",
                "status": ClaimStatus.PENDING,
            },
        )

        # 5. Seed Context Notifications for Demo Users
        Notification.objects.get_or_create(
            recipient=alice,
            notification_type=NotificationType.CLAIM_APPROVED,
            defaults={
                "title": f"Ownership Claim Approved: {sony_item.title}",
                "message": (
                    f"Great news! Your ownership claim for '{sony_item.title}' has been reviewed and APPROVED by the campus desk. "
                    "Please visit the Central Library desk with your student ID to retrieve your item."
                ),
                "target_url": f"/claims/{alice_claim.id}/",
                "is_read": False,
            },
        )

        Notification.objects.get_or_create(
            recipient=bob,
            notification_type=NotificationType.CLAIM_REJECTED,
            defaults={
                "title": f"Claim Status Update: {sony_item.title}",
                "message": (
                    f"Your ownership claim for '{sony_item.title}' was reviewed. Reason: "
                    f"{bob_claim.rejection_reason}"
                ),
                "target_url": f"/claims/{bob_claim.id}/",
                "is_read": True,
            },
        )

        Notification.objects.get_or_create(
            recipient=charlie,
            notification_type=NotificationType.CLAIM_SUBMITTED,
            defaults={
                "title": f"Claim Received: {watch_item.title}",
                "message": f"Your claim for '{watch_item.title}' has been submitted and is currently queued for desk staff evaluation.",
                "target_url": f"/claims/{charlie_claim.id}/",
                "is_read": False,
            },
        )

        Notification.objects.get_or_create(
            recipient=admin_user,
            notification_type=NotificationType.CLAIM_SUBMITTED,
            defaults={
                "title": "New Ownership Claim Awaiting Verification",
                "message": f"{charlie.get_full_name()} filed an ownership claim for '{watch_item.title}'.",
                "target_url": f"/claims/admin/{charlie_claim.id}/",
                "is_read": False,
            },
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded Phase 4 demo data:"))
        self.stdout.write(f"  - Item 1: {sony_item.title} (Status: {sony_item.status})")
        self.stdout.write(f"    * Approved Claim: #{str(alice_claim.id)[:8]} by {alice.username}")
        self.stdout.write(f"    * Rejected Claim: #{str(bob_claim.id)[:8]} by {bob.username}")
        self.stdout.write(f"  - Item 2: {watch_item.title} (Status: {watch_item.status})")
        self.stdout.write(f"    * Pending Claim:  #{str(charlie_claim.id)[:8]} by {charlie.username}")
        self.stdout.write(f"  - Admin Reviewer:   {admin_user.username} ({admin_user.email})")
