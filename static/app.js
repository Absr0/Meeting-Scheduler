(() => {
  const searchForm = document.querySelector("#event-search");
  if (searchForm) {
    const queryInput = document.querySelector("#search-query");
    const categoryInput = document.querySelector("#search-category");
    const cityInput = document.querySelector("#search-city");
    const grid = document.querySelector("#event-grid");
    const count = document.querySelector("#results-count");
    const status = document.querySelector("#search-status");
    let timer;

    const make = (tag, className, text) => {
      const element = document.createElement(tag);
      if (className) element.className = className;
      if (text !== undefined) element.textContent = text;
      return element;
    };

    const renderCard = (event, index) => {
      const card = make("article", "event-card");
      const imageLink = make("a", "event-image-link");
      imageLink.href = `/events/${encodeURIComponent(event.slug)}/`;
      if (event.image_url) {
        const image = make("img", "event-image");
        image.src = event.image_url;
        image.alt = "";
        imageLink.append(image);
      } else {
        const placeholder = make("div", `event-image event-image-placeholder ${index % 4 === 3 ? "tone-four" : ""}`);
        placeholder.append(make("span", "placeholder-spark", "✳"));
        placeholder.append(make("span", "placeholder-word", event.category_label.toUpperCase()));
        imageLink.append(placeholder);
      }
      imageLink.append(make("span", "category-pill", event.category_label));
      card.append(imageLink);

      const body = make("div", "event-card-content");
      const date = new Date(event.starts_at);
      const dateText = new Intl.DateTimeFormat(undefined, { weekday: "short", month: "short", day: "numeric" }).format(date);
      const timeText = new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
      body.append(make("div", "event-date", `${dateText} · ${timeText}`));
      const title = make("h3");
      const titleLink = make("a", "", event.title);
      titleLink.href = imageLink.href;
      title.append(titleLink);
      body.append(title);
      body.append(make("p", "card-location", `⌖ ${event.venue} · ${event.city}`));
      const bottom = make("div", "card-bottom");
      bottom.append(make("span", "", event.confirmed_count ? `${event.confirmed_count} going` : "Be the first to go"));
      const arrow = make("a", "round-arrow", "↗");
      arrow.href = imageLink.href;
      arrow.setAttribute("aria-label", `View ${event.title}`);
      bottom.append(arrow);
      body.append(bottom);
      card.append(body);
      return card;
    };

    const search = async () => {
      const params = new URLSearchParams();
      if (queryInput.value.trim()) params.set("q", queryInput.value.trim());
      if (categoryInput.value) params.set("category", categoryInput.value);
      if (cityInput.value.trim()) params.set("city", cityInput.value.trim());
      status.textContent = "Finding good plans…";
      try {
        const response = await fetch(`${searchForm.dataset.eventsApi}?${params}`, {
          headers: { Accept: "application/json" },
        });
        if (!response.ok) throw new Error("The event search could not be completed.");
        const events = await response.json();
        grid.replaceChildren();
        if (events.length) events.forEach((event, index) => grid.append(renderCard(event, index)));
        else {
          const empty = make("div", "empty-state");
          empty.append(make("span", "empty-icon", "✳"));
          empty.append(make("h3", "", "No gatherings found for those filters."));
          empty.append(make("p", "", "Try another search, or bring the first event to your neighborhood."));
          grid.append(empty);
        }
        count.textContent = `${events.length} upcoming ${events.length === 1 ? "gathering" : "gatherings"}`;
        status.textContent = "";
        const url = new URL(window.location.href);
        ["q", "category", "city"].forEach((key) => {
          const input = searchForm.elements.namedItem(key);
          if (input.value) url.searchParams.set(key, input.value);
          else url.searchParams.delete(key);
        });
        window.history.replaceState({}, "", url);
      } catch (error) {
        status.textContent = error.message;
      }
    };

    searchForm.addEventListener("submit", (event) => {
      event.preventDefault();
      window.clearTimeout(timer);
      search();
    });
    queryInput.addEventListener("input", () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(search, 250);
    });
    categoryInput.addEventListener("change", search);
    cityInput.addEventListener("input", () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(search, 300);
    });
  }

  const csrfToken = (form) => form.querySelector("[name=csrfmiddlewaretoken]")?.value;
  const interactionStatus = document.querySelector("#interaction-status");
  const report = (message) => {
    if (interactionStatus) interactionStatus.textContent = message;
  };

  document.querySelectorAll("[data-rsvp-form]").forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector('button[type="submit"]');
      button.disabled = true;
      report("Saving your RSVP…");
      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken(form), Accept: "application/json" },
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "Your RSVP could not be saved.");
        window.location.reload();
      } catch (error) {
        report(error.message);
        button.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-cancel-rsvp]").forEach((button) => {
    button.addEventListener("click", async () => {
      const form = button.closest("form");
      button.disabled = true;
      report("Cancelling your RSVP…");
      try {
        const response = await fetch(form.dataset.cancelUrl, {
          method: "DELETE",
          headers: { "X-CSRFToken": csrfToken(form), Accept: "application/json" },
        });
        if (!response.ok) throw new Error("Your RSVP could not be cancelled.");
        window.location.reload();
      } catch (error) {
        report(error.message);
        button.disabled = false;
      }
    });
  });

  const reviewForm = document.querySelector("[data-review-form]");
  if (reviewForm) {
    reviewForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = reviewForm.querySelector('button[type="submit"]');
      submit.disabled = true;
      report("Posting your note…");
      try {
        const response = await fetch(reviewForm.action, {
          method: "POST",
          headers: { "X-CSRFToken": csrfToken(reviewForm), Accept: "application/json" },
          body: new FormData(reviewForm),
        });
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || Object.values(payload).flat().join(" "));
        window.location.reload();
      } catch (error) {
        report(error.message);
        submit.disabled = false;
      }
    });
  }
})();
