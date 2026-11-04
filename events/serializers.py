from django.db.models import Avg
from rest_framework import serializers

from events.models import Event, Review, RSVP


class ReviewSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="author.get_full_name", read_only=True)

    class Meta:
        model = Review
        fields = ("id", "author_name", "rating", "body", "created_at")
        read_only_fields = ("id", "author_name", "created_at")


class EventSerializer(serializers.ModelSerializer):
    organizer_name = serializers.CharField(source="organizer.get_full_name", read_only=True)
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    image_url = serializers.SerializerMethodField()
    confirmed_count = serializers.IntegerField(source="going_count", read_only=True)
    average_rating = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            "id",
            "title",
            "slug",
            "category",
            "category_label",
            "description",
            "venue",
            "address",
            "city",
            "starts_at",
            "ends_at",
            "capacity",
            "price",
            "status",
            "image_url",
            "organizer_name",
            "confirmed_count",
            "average_rating",
        )

    def get_image_url(self, event):
        if not event.image:
            return ""
        request = self.context.get("request")
        return request.build_absolute_uri(event.image.url) if request else event.image.url

    def get_average_rating(self, event):
        if hasattr(event, "average_rating"):
            return round(event.average_rating, 1) if event.average_rating is not None else None
        aggregate = event.reviews.aggregate(value=Avg("rating"))
        return round(aggregate["value"], 1) if aggregate["value"] is not None else None


class RSVPSerializer(serializers.ModelSerializer):
    class Meta:
        model = RSVP
        fields = ("id", "status", "created_at")
        read_only_fields = fields
