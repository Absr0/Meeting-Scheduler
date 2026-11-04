from django.db import transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from events.models import Event, Review, RSVP
from events.serializers import EventSerializer, ReviewSerializer, RSVPSerializer


class EventListAPI(generics.ListAPIView):
    serializer_class = EventSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Event.objects.filter(status=Event.Status.PUBLISHED, starts_at__gte=timezone.now())
        query = self.request.query_params.get("q", "").strip()
        category = self.request.query_params.get("category", "").strip()
        city = self.request.query_params.get("city", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(venue__icontains=query)
                | Q(city__icontains=query)
            )
        if category:
            queryset = queryset.filter(category=category)
        if city:
            queryset = queryset.filter(city__icontains=city)
        return queryset.annotate(
            going_count=Count("rsvps", filter=Q(rsvps__status=RSVP.Status.CONFIRMED), distinct=True),
            average_rating=Avg("reviews__rating"),
        ).select_related("organizer").prefetch_related("reviews", "rsvps")


class EventDetailAPI(generics.RetrieveAPIView):
    serializer_class = EventSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = "slug"
    queryset = Event.objects.filter(status=Event.Status.PUBLISHED).annotate(
        going_count=Count("rsvps", filter=Q(rsvps__status=RSVP.Status.CONFIRMED), distinct=True),
        average_rating=Avg("reviews__rating"),
    ).select_related("organizer").prefetch_related("reviews", "rsvps")


class ReviewListCreateAPI(generics.ListCreateAPIView):
    serializer_class = ReviewSerializer
    queryset = Review.objects.select_related("author")

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        return super().get_queryset().filter(event__slug=self.kwargs["slug"], event__status=Event.Status.PUBLISHED)

    def perform_create(self, serializer):
        event = get_object_or_404(Event, slug=self.kwargs["slug"], status=Event.Status.PUBLISHED)
        if event.ends_at > timezone.now():
            raise ValidationError({"detail": "Reviews open after the event has ended."})
        if Review.objects.filter(event=event, author=self.request.user).exists():
            raise ValidationError({"detail": "You have already reviewed this event."})
        serializer.save(event=event, author=self.request.user)


class RSVPAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, slug):
        event = get_object_or_404(
            Event.objects.select_for_update(),
            slug=slug,
            status=Event.Status.PUBLISHED,
        )
        if event.starts_at <= timezone.now():
            raise ValidationError({"detail": "This event has already started."})

        rsvp = RSVP.objects.filter(event=event, user=request.user).first()
        if rsvp and rsvp.status == RSVP.Status.CONFIRMED:
            return Response(RSVPSerializer(rsvp).data, status=status.HTTP_200_OK)
        if event.capacity is not None and event.rsvps.filter(status=RSVP.Status.CONFIRMED).count() >= event.capacity:
            raise ValidationError({"detail": "This event is full."})
        if rsvp:
            rsvp.status = RSVP.Status.CONFIRMED
            rsvp.save(update_fields=["status"])
            created = False
        else:
            rsvp = RSVP.objects.create(event=event, user=request.user)
            created = True
        return Response(RSVPSerializer(rsvp).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @transaction.atomic
    def delete(self, request, slug):
        event = get_object_or_404(Event, slug=slug, status=Event.Status.PUBLISHED)
        rsvp = get_object_or_404(RSVP, event=event, user=request.user)
        rsvp.status = RSVP.Status.CANCELLED
        rsvp.save(update_fields=["status"])
        return Response(status=status.HTTP_204_NO_CONTENT)
