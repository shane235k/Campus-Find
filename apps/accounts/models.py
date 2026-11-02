"""Models for accounts application.

Phase 0.1 introduces the foundational CampusUser model (inheriting AbstractUser)
to establish AUTH_USER_MODEL before any dependent application models or migrations are generated.
Full profile extensions (campus_id, department, role, student verification) will be implemented in Phase 1.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models


class CampusUser(AbstractUser):
    """Custom User model for Campus Lost & Found Hub."""

    class Meta:
        verbose_name = "Campus User"
        verbose_name_plural = "Campus Users"
