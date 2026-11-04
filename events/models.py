from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class Event(models.Model):
    class Category(models.TextChoices):
        ARTS = "arts", "Arts & culture"
        FOOD = "food", "Food & drink"
        MUSIC = "music", "Music"
        OUTDOORS = "outdoors", "Outdoors"
        SOCIAL = "social", "Social"
        TECH = "tech", "Technology"
        WELLNESS = "wellness", "Wellness"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"

    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_events",
    )
    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.SOCIAL)
    description = models.TextField()
    venue = models.CharField(max_length=180)
    address = models.CharField(max_length=240, blank=True)
    city = models.CharField(max_length=100, default="Local area")
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField()
    capacity = models.PositiveIntegerField(null=True, blank=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    image = models.ImageField(upload_to="events/", blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PUBLISHED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["starts_at"]
        indexes = [models.Index(fields=["status", "starts_at"])]

    def __str__(self):
        return self.title

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "The end time must be after the start time."})
        if self.capacity == 0:
            raise ValidationError({"capacity": "Capacity must be greater than zero, or left blank for unlimited."})

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:150] or "event"
            slug = base_slug
            suffix = 2
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug[:145]}-{suffix}"
                suffix += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def confirmed_count(self):
        return self.rsvps.filter(status=RSVP.Status.CONFIRMED).count()

    @property
    def is_full(self):
        return self.capacity is not None and self.confirmed_count >= self.capacity


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=100, blank=True)
    bio = models.CharField(max_length=280, blank=True)
    city = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to="profiles/", blank=True)
    is_organizer = models.BooleanField(default=False)

    def __str__(self):
        return self.display_name or self.user.get_username()


class RSVP(models.Model):
    class Status(models.TextChoices):
        CONFIRMED = "confirmed", "Going"
        CANCELLED = "cancelled", "Cancelled"

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="rsvps")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="rsvps")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CONFIRMED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "user"], name="unique_event_rsvp_per_user"),
        ]
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.user} — {self.event}"


class Review(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="reviews")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="event_reviews")
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    body = models.TextField(max_length=1200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["event", "author"], name="unique_event_review_per_author"),
            models.CheckConstraint(condition=models.Q(rating__gte=1, rating__lte=5), name="review_rating_between_1_and_5"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rating}/5 — {self.event}"
