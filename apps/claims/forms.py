"""Forms for student claim submissions and administrative verification review."""
from django import forms
from django.core.exceptions import ValidationError

from .models import Claim, ClaimStatus


class ClaimSubmissionForm(forms.ModelForm):
    """Student submission form for ownership verification proof."""

    class Meta:
        model = Claim
        fields = [
            "claim_description",
            "distinguishing_features",
            "item_contents",
            "last_seen_details",
            "evidence_file",
        ]
        widgets = {
            "claim_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Explain how you came to misplace this item, approximate date/time, and general context...",
                }
            ),
            "distinguishing_features": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Mention details NOT listed publicly: serial numbers, secret scratches, stickers, engravings, case brands, lockscreen wallpaper, or password hints...",
                }
            ),
            "item_contents": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "If this was a bag, wallet, or notebook: list specific internal items, cards, currency, or receipts...",
                }
            ),
            "last_seen_details": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g., Central Library 2nd floor study carrel #14 on Oct 28 at 4:30 PM",
                }
            ),
            "evidence_file": forms.FileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".jpg,.jpeg,.png,.webp,.pdf",
                }
            ),
        }
        help_texts = {
            "distinguishing_features": "Critical: This confidential information is used by staff to verify you are the genuine owner.",
            "evidence_file": "Optional: Upload invoice, store receipt, photo of owner with item, or warranty card (max 5 MB, PDF/Image).",
        }

    def clean_distinguishing_features(self):
        features = self.cleaned_data.get("distinguishing_features", "").strip()
        if len(features) < 15:
            raise ValidationError(
                "Please provide a more descriptive distinguishing feature (minimum 15 characters) to help staff verify ownership."
            )
        return features


class ClaimReviewForm(forms.Form):
    """Admin form to moderate, investigate, approve, or reject an ownership claim."""

    ACTION_CHOICES = [
        ("under_review", "Move to Under Review"),
        ("approve", "Approve Claim & Mark Item Resolved"),
        ("reject", "Reject Claim"),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.RadioSelect(attrs={"class": "form-check-input"}),
        initial="under_review",
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Confidential investigation notes for staff members (hidden from claimant)...",
            }
        ),
        help_text="Internal records for campus security and desk staff.",
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Explain to the student why this claim was not approved (e.g., serial number mismatch)...",
            }
        ),
        help_text="This message will be sent to the student if the claim is rejected.",
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get("action")
        rejection_reason = cleaned_data.get("rejection_reason", "").strip()

        if action == "reject" and not rejection_reason:
            self.add_error(
                "rejection_reason",
                "A rejection reason must be provided when rejecting a claim so the student understands the decision.",
            )

        return cleaned_data

