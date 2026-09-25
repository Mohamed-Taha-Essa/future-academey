from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ("name", "email", "phone", "message")
        labels = {
            "name": _("Full Name"),
            "email": _("Email Address"),
            "phone": _("Phone Number"),
            "message": _("Your Message"),
        }
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Your full name"),
                    "maxlength": 150,
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("name@example.com"),
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": _("e.g. 201001234567"),
                    "maxlength": 32,
                }
            ),
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": _("Write your message here..."),
                    "rows": 4,
                }
            ),
        }

    def clean(self):
        cleaned = super().clean()
        for field in ("name", "email", "phone", "message"):
            value = cleaned.get(field)
            if isinstance(value, str):
                cleaned[field] = value.strip()
        return cleaned
