"""Forms for student registration, authentication, profile management, and admin provisioning."""
from django import forms
from django.conf import settings
from django.contrib.auth import authenticate, password_validation
from django.core.exceptions import ValidationError
from PIL import Image

from .models import CampusUser
from .throttling import is_rate_limited, record_failed_attempt, reset_throttle


class StudentRegistrationForm(forms.ModelForm):
    """Student registration form enforcing university domain and credentials."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "First Name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Last Name"}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "student@university.edu"}),
        help_text="Must be an approved campus email address.",
    )
    student_id = forms.CharField(
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g., STU-2026-9812"}),
        help_text="Official university registration or roll number.",
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Optional Phone Number"}),
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Enter secure password"}),
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm password"}),
    )

    class Meta:
        model = CampusUser
        fields = ("first_name", "last_name", "email", "student_id", "phone_number")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if not email:
            raise ValidationError("Email address is required.")

        # Check duplicate email
        if CampusUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this university email address already exists.")

        # Enforce approved university domain
        allowed_domains = getattr(settings, "UNIVERSITY_EMAIL_DOMAINS", ["university.edu"])
        if allowed_domains and "*" not in allowed_domains:
            domain = email.split("@")[-1].lower()
            normalized_allowed = [d.lower().strip() for d in allowed_domains]
            if domain not in normalized_allowed:
                raise ValidationError(
                    f"Registration is restricted to university email domains ({', '.join(allowed_domains)})."
                )
        return email

    def clean_student_id(self):
        student_id = self.cleaned_data.get("student_id", "").strip()
        if not student_id:
            raise ValidationError("Student registration number is required.")

        if CampusUser.objects.filter(student_id__iexact=student_id).exists():
            raise ValidationError("A student with this registration number has already registered.")
        return student_id

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
            else:
                # Validate password against Django's validators
                user_stub = CampusUser(
                    username=cleaned_data.get("email", ""),
                    email=cleaned_data.get("email", ""),
                )
                password_validation.validate_password(password, user=user_stub)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"].lower()
        user.set_password(self.cleaned_data["password"])
        # Server-side forced role assignment: users never choose their role
        user.role = CampusUser.Role.STUDENT
        user.is_staff = False
        user.is_superuser = False
        user.is_email_verified = False  # Real verification required in future

        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    """User authentication form supporting email or username login with throttling."""

    email = forms.CharField(
        label="University Email or Username",
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "name@university.edu or username", "autofocus": True}
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Password"}),
    )

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        identifier = cleaned_data.get("email", "").strip().lower()
        password = cleaned_data.get("password")

        if identifier and password:
            # Check rate limiting / brute-force lockout
            if is_rate_limited(self.request, identifier):
                raise ValidationError(
                    "Too many failed login attempts. For security reasons, please wait 15 minutes before trying again."
                )

            # Authenticate user
            self.user_cache = authenticate(
                self.request,
                username=identifier,
                password=password,
            )

            if self.user_cache is None:
                record_failed_attempt(self.request, identifier)
                raise ValidationError("Invalid email/username or password. Please verify your credentials.")
            elif not self.user_cache.is_active:
                raise ValidationError("This account has been deactivated. Please contact campus security.")
            else:
                reset_throttle(self.request, identifier)

        return cleaned_data

    def get_user(self):
        return self.user_cache


class ProfileUpdateForm(forms.ModelForm):
    """Profile editing form with strict protection over role and identifiers."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "+91 98765 43210"}),
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={"class": "form-control", "accept": "image/jpeg,image/png,image/webp"}),
    )

    class Meta:
        model = CampusUser
        # Excludes student_id, email, role, is_email_verified to prevent tampering
        fields = ("first_name", "last_name", "phone_number", "profile_picture")

    def clean_profile_picture(self):
        picture = self.cleaned_data.get("profile_picture")
        if not picture:
            return picture

        # Check maximum file size (2 MB)
        max_size = 2 * 1024 * 1024
        if picture.size > max_size:
            raise ValidationError("Profile picture file size cannot exceed 2 MB.")

        # Validate image content using Pillow
        try:
            img = Image.open(picture)
            img.verify()
        except Exception:
            raise ValidationError("Uploaded file is not a valid or readable image.")

        return picture


class AdminProvisioningForm(forms.ModelForm):
    """Super Admin-only form to provision administrative staff accounts."""

    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Administrator First Name"}),
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Administrator Last Name"}),
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={"class": "form-control", "placeholder": "admin@university.edu"}),
    )
    phone_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Office Contact Phone"}),
    )
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Initial secure password"}),
    )
    confirm_password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirm password"}),
    )

    class Meta:
        model = CampusUser
        fields = ("first_name", "last_name", "email", "phone_number")

    def clean_email(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        if CampusUser.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password:
            if password != confirm_password:
                self.add_error("confirm_password", "Passwords do not match.")
            else:
                password_validation.validate_password(password)
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["email"].lower()
        user.set_password(self.cleaned_data["password"])
        # Server-side enforcement: strictly ADMIN, never SUPER_ADMIN
        user.role = CampusUser.Role.ADMIN
        user.is_staff = True
        user.is_superuser = False
        user.is_email_verified = True

        if commit:
            user.save()
        return user

