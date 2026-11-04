from django.contrib import admin

from events.models import Event, Profile, Review, RSVP


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "city", "starts_at", "status", "organizer")
    list_filter = ("status", "category", "city")
    search_fields = ("title", "description", "venue", "city", "organizer__username")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "starts_at"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "city", "is_organizer")
    list_filter = ("is_organizer", "city")
    search_fields = ("display_name", "user__username", "city")


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = ("event", "user", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("event__title", "user__username")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("event", "author", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("event__title", "author__username", "body")
