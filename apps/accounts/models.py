"""Models for accounts application.

CampusUser inherits from AbstractUser and implements role-based access control,
university email normalization, student identification, and profile attributes.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


class CampusUser(AbstractUser):
    """Custom User model for Campus Lost & Found Hub."""

    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        ADMIN = "ADMIN", "Administrator"
        SUPER_ADMIN = "SUPER_ADMIN", "Super Administrator"

    # Enforce unique and normalized email
    email = models.EmailField(
        "email address",
        unique=True,
        error_messages={
            "unique": "A user with that email address already exists.",
        },
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        help_text="Designates application level role and permissions.",
    )

    phone_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Optional contact phone number for item recovery notifications.",
    )

    profile_picture = models.ImageField(
        upload_to="profile_pics/%Y/%m/",
        blank=True,
        null=True,
        help_text="User profile picture.",
    )

    student_id = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        default=None,
        help_text="University student registration / roll number (unique for students).",
    )

    is_email_verified = models.BooleanField(
        default=False,
        help_text="Designates whether the user's university email address has been verified.",
    )

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        help_text="Timestamp when the user account was created.",
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Timestamp when the user account was last updated.",
    )

    class Meta:
        verbose_name = "Campus User"
        verbose_name_plural = "Campus Users"
        constraints = [
            # Ensure student_id is unique when provided (allows multiple nulls/blanks for admins)
            models.UniqueConstraint(
                fields=["student_id"],
                name="unique_student_id_when_provided",
                condition=models.Q(student_id__isnull=False) & ~models.Q(student_id=""),
            )
        ]

    def __str__(self):
        full_name = self.get_full_name()
        display = full_name if full_name else self.username
        return f"{display} ({self.get_role_display()})"

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email).lower()
        if self.student_id:
            self.student_id = self.student_id.strip()
            if not self.student_id:
                self.student_id = None
        else:
            self.student_id = None

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.__class__.objects.normalize_email(self.email).lower()
        if self.student_id:
            self.student_id = self.student_id.strip()
            if not self.student_id:
                self.student_id = None
        else:
            self.student_id = None

        # Synchronize Django staff/superuser flags with application roles
        if self.role == self.Role.SUPER_ADMIN:
            self.is_staff = True
            self.is_superuser = True
        elif self.role == self.Role.ADMIN:
            self.is_staff = True
            self.is_superuser = False
        elif self.role == self.Role.STUDENT:
            if not self.is_superuser and not self.is_staff:
                self.is_staff = False
                self.is_superuser = False

        super().save(*args, **kwargs)

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_admin_user(self):
        return self.role in [self.Role.ADMIN, self.Role.SUPER_ADMIN]

    @property
    def is_super_admin(self):
        return self.role == self.Role.SUPER_ADMIN
