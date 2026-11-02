"""Authentication backends for Campus Lost & Found Hub."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrUsernameModelBackend(ModelBackend):
    """Allows authentication with email address (primary) or username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD) or kwargs.get("email")

        if not username or not password:
            return None

        username_clean = username.strip().lower()

        try:
            # Query case-insensitively by email or username
            user = UserModel.objects.filter(
                Q(email__iexact=username_clean) | Q(username__iexact=username_clean)
            ).first()
        except Exception:
            return None

        if user and user.check_password(password):
            return user
        return None

    def user_can_authenticate(self, user):
        """Allow returning inactive users so LoginForm can raise specific deactivation notice."""
        return True
