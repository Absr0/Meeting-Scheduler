# Aroundabout

Aroundabout is a local event and meetup directory built with Django. Neighbors can discover gatherings by keyword, category, or city; create profiles; RSVP; and leave one review per event. Event hosts get a personal dashboard, and staff can manage the full directory in Django Admin.

## Run locally

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Sign up to post events and RSVP. The superuser dashboard is at `/admin/`.

Uploaded event and profile images are stored in the local `media/` directory. SQLite is used by default. Set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, and `DJANGO_TIME_ZONE` in the environment when configuring a deployment.

## Features

- Django authentication, registration, editable profiles, and organizer permissions
- Event categories, locations, schedules, capacity, price, publication status, and image uploads
- Model validation, unique slugs, foreign keys, indexes, aggregate counts, and database constraints
- Organizer dashboard and searchable/filterable Django Admin
- Capacity-aware, idempotent RSVPs and one rating/review per person and event
- Django REST Framework endpoints with session authentication and permissions
- Debounced live event search, asynchronous RSVP/cancel actions, and asynchronous review submission

## API

- `GET /api/events/?q=music&category=music&city=Northside`
- `GET /api/events/<slug>/`
- `GET /api/events/<slug>/reviews/`
- `POST /api/events/<slug>/reviews/` — authenticated; JSON or form data with `rating` (1–5) and `body`
- `POST /api/events/<slug>/rsvp/` — authenticated
- `DELETE /api/events/<slug>/rsvp/` — authenticated
