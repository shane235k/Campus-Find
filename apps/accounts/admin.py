"""Admin configuration for accounts app."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CampusUser

admin.site.register(CampusUser, UserAdmin)
