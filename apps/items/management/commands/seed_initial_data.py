"""Management command to seed initial active categories and campus locations idempotently."""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.items.models import CampusLocation, Category

INITIAL_CATEGORIES = [
    {
        "name": "Electronics & Gadgets",
        "description": "Laptops, smartphones, chargers, headphones, calculators, tablets, and cables.",
    },
    {
        "name": "Student IDs & Wallets",
        "description": "Campus smartcards, driver licenses, debit cards, wallets, and money clips.",
    },
    {
        "name": "Keys & Access Cards",
        "description": "Dorm keys, locker keys, car fobs, and RFID access credentials.",
    },
    {
        "name": "Bags & Backpacks",
        "description": "School backpacks, messenger bags, gym duffels, and tote bags.",
    },
    {
        "name": "Books & Stationeries",
        "description": "Course textbooks, lecture notebooks, binders, pencil cases, and calculators.",
    },
    {
        "name": "Bottles & Containers",
        "description": "Insulated water bottles, coffee tumblers, food containers, and flasks.",
    },
    {
        "name": "Clothing & Apparel",
        "description": "Jackets, hoodies, caps, gloves, scarves, and umbrellas.",
    },
    {
        "name": "Eyewear & Accessories",
        "description": "Prescription eyeglasses, sunglasses, jewelry, smartwatches, and rings.",
    },
]

INITIAL_LOCATIONS = [
    {
        "name": "Central University Library",
        "description": "Main campus library including circulation desk, 2nd floor silent reading rooms, and cafe area.",
    },
    {
        "name": "Student Activity Center",
        "description": "Campus student union building, ground floor information counter, and lounge spaces.",
    },
    {
        "name": "Main Dining Hall & Cafeteria",
        "description": "Central dining hall, food court counters, and outdoor seating patio.",
    },
    {
        "name": "Science & Technology Complex",
        "description": "Science lecture theaters, biology and chemistry labs, and north entrance atrium.",
    },
    {
        "name": "Engineering Center (Block B)",
        "description": "Engineering workshops, computing clusters, and ground floor concourse.",
    },
    {
        "name": "Sports & Recreation Center",
        "description": "Campus gymnasium, indoor basketball courts, locker rooms, and track field.",
    },
    {
        "name": "Administration & Security Office",
        "description": "Registrar desks, campus safety office, and lost & found centralized lockup.",
    },
]


class Command(BaseCommand):
    help = "Idempotently populate foundational categories and campus locations."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulate initial data seeding without committing database records.",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run", False)

        categories_created = 0
        categories_existing = 0
        locations_created = 0
        locations_existing = 0

        with transaction.atomic():
            self.stdout.write(self.style.NOTICE("Seeding foundational categories..."))
            for cat_data in INITIAL_CATEGORIES:
                if dry_run:
                    exists = Category.objects.filter(name=cat_data["name"]).exists()
                    if exists:
                        categories_existing += 1
                    else:
                        categories_created += 1
                else:
                    _, created = Category.objects.get_or_create(
                        name=cat_data["name"],
                        defaults={"description": cat_data["description"], "is_active": True},
                    )
                    if created:
                        categories_created += 1
                        self.stdout.write(f"  + Created Category: {cat_data['name']}")
                    else:
                        categories_existing += 1

            self.stdout.write(self.style.NOTICE("\nSeeding foundational campus locations..."))
            for loc_data in INITIAL_LOCATIONS:
                if dry_run:
                    exists = CampusLocation.objects.filter(name=loc_data["name"]).exists()
                    if exists:
                        locations_existing += 1
                    else:
                        locations_created += 1
                else:
                    _, created = CampusLocation.objects.get_or_create(
                        name=loc_data["name"],
                        defaults={"description": loc_data["description"], "is_active": True},
                    )
                    if created:
                        locations_created += 1
                        self.stdout.write(f"  + Created Location: {loc_data['name']}")
                    else:
                        locations_existing += 1

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write(
                    self.style.WARNING(
                        f"\n[DRY RUN] Would create {categories_created} categories and {locations_created} locations."
                    )
                )
                return

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSeeding complete:\n"
                f"  Categories: {categories_created} created, {categories_existing} already present\n"
                f"  Locations:  {locations_created} created, {locations_existing} already present\n"
            )
        )

