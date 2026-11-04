from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from events.models import Event, RSVP, Review


class EventDirectoryTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user(username="organizer", password="test-pass-123")
        self.attendee = User.objects.create_user(username="attendee", password="test-pass-123")
        self.event = Event.objects.create(
            organizer=self.organizer,
            title="Neighborhood picnic",
            category=Event.Category.OUTDOORS,
            description="Meet your neighbors.",
            venue="Riverside Park",
            city="Northside",
            starts_at=timezone.now() + timedelta(days=4),
            ends_at=timezone.now() + timedelta(days=4, hours=2),
            capacity=1,
            price=Decimal("0.00"),
        )

    def test_slug_is_generated_and_unique(self):
        another = Event.objects.create(
            organizer=self.organizer,
            title=self.event.title,
            category=Event.Category.SOCIAL,
            description="A second event.",
            venue="Community Hall",
            starts_at=timezone.now() + timedelta(days=5),
            ends_at=timezone.now() + timedelta(days=5, hours=1),
        )
        self.assertEqual(self.event.slug, "neighborhood-picnic")
        self.assertEqual(another.slug, "neighborhood-picnic-2")

    def test_directory_filters_by_city_and_category(self):
        response = self.client.get(reverse("home"), {"city": "North", "category": Event.Category.OUTDOORS})
        self.assertContains(response, "Neighborhood picnic")
        self.assertEqual(len(response.context["events"]), 1)

    def test_draft_event_is_only_visible_to_its_organizer(self):
        self.event.status = Event.Status.DRAFT
        self.event.save()
        detail_url = reverse("event_detail", kwargs={"slug": self.event.slug})
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        self.client.force_login(self.organizer)
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "DRAFT")

    def test_rsvp_capacity_and_idempotency(self):
        self.client.force_login(self.attendee)
        first = self.client.post(reverse("event_rsvp", kwargs={"slug": self.event.slug}))
        second = self.client.post(reverse("event_rsvp", kwargs={"slug": self.event.slug}))
        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302)
        self.assertEqual(RSVP.objects.filter(event=self.event, status=RSVP.Status.CONFIRMED).count(), 1)

    def test_capacity_rejects_a_second_attendee(self):
        self.client.force_login(self.attendee)
        self.client.post(reverse("event_rsvp", kwargs={"slug": self.event.slug}))
        another = User.objects.create_user(username="another", password="test-pass-123")
        self.client.force_login(another)
        self.client.post(reverse("event_rsvp", kwargs={"slug": self.event.slug}))
        self.assertFalse(RSVP.objects.filter(event=self.event, user=another).exists())

    def test_rsvp_api_allows_the_first_spot(self):
        client = APIClient()
        client.force_authenticate(self.attendee)
        response = client.post(reverse("api_rsvp", kwargs={"slug": self.event.slug}))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RSVP.objects.filter(event=self.event, status=RSVP.Status.CONFIRMED).count(), 1)

    def test_review_api_requires_authentication_and_limits_duplicate_reviews(self):
        self.event.ends_at = timezone.now() - timedelta(hours=1)
        self.event.starts_at = timezone.now() - timedelta(hours=3)
        self.event.save()
        url = reverse("api_reviews", kwargs={"slug": self.event.slug})
        response = self.client.post(url, {"rating": 5, "body": "Lovely event."}, content_type="application/json")
        self.assertEqual(response.status_code, 403)
        client = APIClient()
        client.force_authenticate(self.attendee)
        response = client.post(url, {"rating": 5, "body": "Lovely event."}, format="json")
        duplicate = client.post(url, {"rating": 4, "body": "Another review."}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(Review.objects.filter(event=self.event, author=self.attendee).count(), 1)

    def test_event_api_search(self):
        response = self.client.get(reverse("api_events"), {"q": "Riverside"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
