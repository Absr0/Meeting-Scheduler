from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.urls import reverse, reverse_lazy

from events.forms import EventForm, ProfileForm, SignupForm
from events.models import Event, Profile, RSVP


class HomeView(ListView):
    template_name = "events/home.html"
    context_object_name = "events"
    queryset = Event.objects.filter(status=Event.Status.PUBLISHED).annotate(
        going_count=Count("rsvps", filter=Q(rsvps__status=RSVP.Status.CONFIRMED), distinct=True),
        rating_average=Avg("reviews__rating"),
    ).select_related("organizer")

    def get_queryset(self):
        queryset = super().get_queryset().filter(starts_at__gte=timezone.now())
        query = self.request.GET.get("q", "").strip()
        category = self.request.GET.get("category", "").strip()
        city = self.request.GET.get("city", "").strip()
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | Q(description__icontains=query) | Q(venue__icontains=query)
            )
        if category:
            queryset = queryset.filter(category=category)
        if city:
            queryset = queryset.filter(city__icontains=city)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["categories"] = Event.Category.choices
        return context


class EventDetailView(DetailView):
    model = Event
    template_name = "events/detail.html"
    context_object_name = "event"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_queryset(self):
        queryset = Event.objects.select_related("organizer").prefetch_related("reviews__author", "rsvps")
        if self.request.user.is_staff:
            return queryset
        if self.request.user.is_authenticated:
            return queryset.filter(Q(status=Event.Status.PUBLISHED) | Q(organizer=self.request.user))
        return queryset.filter(status=Event.Status.PUBLISHED)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        event = self.object
        context["reviews"] = event.reviews.select_related("author").all()
        context["going_count"] = event.rsvps.filter(status=RSVP.Status.CONFIRMED).count()
        context["already_going"] = self.request.user.is_authenticated and event.rsvps.filter(
            user=self.request.user, status=RSVP.Status.CONFIRMED
        ).exists()
        context["has_reviewed"] = self.request.user.is_authenticated and event.reviews.filter(
            author=self.request.user
        ).exists()
        context["average_rating"] = event.reviews.aggregate(value=Avg("rating"))["value"]
        context["can_review"] = event.ends_at <= timezone.now()
        context["spots_left"] = max(event.capacity - context["going_count"], 0) if event.capacity else None
        return context


class EventCreateView(LoginRequiredMixin, CreateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"

    def form_valid(self, form):
        form.instance.organizer = self.request.user
        profile = self.request.user.profile
        if not profile.is_organizer:
            profile.is_organizer = True
            profile.save(update_fields=["is_organizer"])
        messages.success(self.request, "Your event has been saved.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("event_detail", kwargs={"slug": self.object.slug})


class EventUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Event
    form_class = EventForm
    template_name = "events/event_form.html"
    slug_field = "slug"

    def test_func(self):
        event = self.get_object()
        return self.request.user.is_staff or event.organizer_id == self.request.user.id

    def get_success_url(self):
        return reverse("event_detail", kwargs={"slug": self.object.slug})


class OrganizerDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    template_name = "events/organizer_dashboard.html"
    context_object_name = "events"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.profile.is_organizer

    def get_queryset(self):
        queryset = Event.objects.annotate(rsvp_count=Count("rsvps", filter=Q(rsvps__status=RSVP.Status.CONFIRMED)))
        if not self.request.user.is_staff:
            queryset = queryset.filter(organizer=self.request.user)
        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["published_count"] = context["events"].filter(status=Event.Status.PUBLISHED).count()
        context["rsvp_total"] = sum(event.rsvp_count for event in context["events"])
        return context


class ProfileView(LoginRequiredMixin, UpdateView):
    model = Profile
    form_class = ProfileForm
    template_name = "events/profile.html"
    success_url = reverse_lazy("profile")

    def get_object(self, queryset=None):
        return self.request.user.profile

    def form_valid(self, form):
        messages.success(self.request, "Profile updated.")
        return super().form_valid(form)


def signup(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome! Your profile is ready.")
        return redirect("home")
    return render(request, "registration/signup.html", {"form": form})


def rsvp_event(request, slug):
    if request.method != "POST":
        return redirect("event_detail", slug=slug)
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={request.path}")
    with transaction.atomic():
        event = get_object_or_404(Event.objects.select_for_update(), slug=slug, status=Event.Status.PUBLISHED)
        if event.starts_at <= timezone.now():
            messages.error(request, "This event has already started.")
        else:
            rsvp = RSVP.objects.filter(event=event, user=request.user).first()
            if rsvp and rsvp.status == RSVP.Status.CONFIRMED:
                messages.info(request, "You're already on the guest list.")
            elif event.capacity is not None and event.rsvps.filter(status=RSVP.Status.CONFIRMED).count() >= event.capacity:
                messages.error(request, "Sorry, this event is full.")
            elif rsvp:
                rsvp.status = RSVP.Status.CONFIRMED
                rsvp.save(update_fields=["status"])
                messages.success(request, "You're going! See you there.")
            else:
                RSVP.objects.create(event=event, user=request.user)
                messages.success(request, "You're going! See you there.")
    return redirect("event_detail", slug=slug)


def cancel_rsvp(request, slug):
    if request.method == "POST" and request.user.is_authenticated:
        RSVP.objects.filter(event__slug=slug, user=request.user, status=RSVP.Status.CONFIRMED).update(
            status=RSVP.Status.CANCELLED
        )
        messages.info(request, "Your RSVP was cancelled.")
    return redirect("event_detail", slug=slug)
