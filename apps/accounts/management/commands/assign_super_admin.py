"""Management command to securely assign the Super Admin role to an existing user."""
import logging
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger(__name__)
CampusUser = get_user_model()


class Command(BaseCommand):
    help = (
        "Securely promote an existing CampusUser to SUPER_ADMIN role. "
        "Requires an explicit user email or username. Does not accept or create passwords."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "identifier",
            type=str,
            help="University email address or username of the existing user account to promote.",
        )
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_true",
            help="Do not prompt for confirmation before role assignment.",
        )

    def handle(self, *args, **options):
        identifier = options["identifier"].strip()
        no_input = options.get("noinput", False)

        if not identifier:
            raise CommandError("An account identifier (email or username) is required.")

        normalized_email = CampusUser.objects.normalize_email(identifier).lower()

        # Query user by email (case-insensitive) or username
        try:
            user = CampusUser.objects.filter(
                email__iexact=normalized_email
            ).first() or CampusUser.objects.filter(username__iexact=identifier).first()

            if not user:
                raise CommandError(
                    f"No CampusUser account found matching identifier '{identifier}'. "
                    "Ensure the user account has already been registered."
                )

        except Exception as exc:
            if isinstance(exc, CommandError):
                raise
            raise CommandError(f"Database query error while locating user: {exc}") from exc

        previous_role = user.get_role_display()

        if user.role == CampusUser.Role.SUPER_ADMIN and user.is_superuser and user.is_staff:
            self.stdout.write(
                self.style.WARNING(
                    f"Account '{user.email}' (Username: {user.username}) is already a configured Super Administrator."
                )
            )
            return

        # Confirmation prompt if interactive
        if not no_input:
            self.stdout.write(
                f"\nAbout to promote account to Super Administrator:\n"
                f"  Username:      {user.username}\n"
                f"  Email:         {user.email}\n"
                f"  Current Role:  {previous_role}\n"
                f"  Target Role:   Super Administrator (SUPER_ADMIN)\n"
            )
            confirm = input("Are you sure you want to proceed? [y/N]: ").strip().lower()
            if confirm not in ("y", "yes"):
                self.stdout.write(self.style.NOTICE("Super Admin assignment cancelled by operator."))
                return

        # Perform atomic role update
        with transaction.atomic():
            user.role = CampusUser.Role.SUPER_ADMIN
            user.is_staff = True
            user.is_superuser = True
            user.save()

        logger.info(
            "Security role elevation: Account %s (%s) promoted from %s to SUPER_ADMIN by management command",
            user.email,
            user.username,
            previous_role,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully elevated '{user.email}' to Super Administrator (SUPER_ADMIN) role!\n"
                f"  Staff Status:     is_staff={user.is_staff}\n"
                f"  Superuser Status: is_superuser={user.is_superuser}\n"
                f"  Django Admin:     Granted access at /admin/\n"
                f"  Super Admin Desk: Granted access at /dashboard/super-admin/\n"
            )
        )

