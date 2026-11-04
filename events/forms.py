from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from events.models import Event, Profile, Review


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title",
            "category",
            "description",
            "venue",
            "address",
            "city",
            "starts_at",
            "ends_at",
            "capacity",
            "price",
            "image",
            "status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "capacity": forms.NumberInput(attrs={"min": 1}),
            "price": forms.NumberInput(attrs={"min": 0, "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in ("starts_at", "ends_at"):
            self.fields[field].input_formats = ["%Y-%m-%dT%H:%M"]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        if image and image.size > 5 * 1024 * 1024:
            raise ValidationError("Image must be 5 MB or smaller.")
        return image


class SignupForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True, label="Name")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "email")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ("display_name", "bio", "city", "avatar", "is_organizer")
        widgets = {"bio": forms.Textarea(attrs={"rows": 3})}

    def clean_avatar(self):
        image = self.cleaned_data.get("avatar")
        if image and image.size > 5 * 1024 * 1024:
            raise ValidationError("Image must be 5 MB or smaller.")
        return image


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("rating", "body")
