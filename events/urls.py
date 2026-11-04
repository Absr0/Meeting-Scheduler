from django.urls import path

from events import api, views


urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("events/new/", views.EventCreateView.as_view(), name="event_create"),
    path("events/<slug:slug>/", views.EventDetailView.as_view(), name="event_detail"),
    path("events/<slug:slug>/edit/", views.EventUpdateView.as_view(), name="event_edit"),
    path("events/<slug:slug>/rsvp/", views.rsvp_event, name="event_rsvp"),
    path("events/<slug:slug>/cancel-rsvp/", views.cancel_rsvp, name="event_cancel_rsvp"),
    path("organizer/", views.OrganizerDashboardView.as_view(), name="organizer_dashboard"),
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("signup/", views.signup, name="signup"),
    path("api/events/", api.EventListAPI.as_view(), name="api_events"),
    path("api/events/<slug:slug>/", api.EventDetailAPI.as_view(), name="api_event_detail"),
    path("api/events/<slug:slug>/reviews/", api.ReviewListCreateAPI.as_view(), name="api_reviews"),
    path("api/events/<slug:slug>/rsvp/", api.RSVPAPI.as_view(), name="api_rsvp"),
]
