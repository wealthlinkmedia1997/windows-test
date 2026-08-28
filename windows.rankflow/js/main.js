// ============================================================
// Shared logic used across all pages: testimonial rendering,
// video facades, lead form handling + routing, GHL calendar
// lazy-load, Google Places autocomplete.
// ============================================================

// ---------- Icons (inline SVG, no external icon library) ----------
const ICON_SHIELD = `<svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5l-8-3Z" fill="#2563eb"/>
  <path d="M8.5 12.5l2.5 2.5 4.5-5" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
</svg>`;
const ICON_PIN = `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z"/><circle cx="12" cy="10" r="2.6"/></svg>`;
const ICON_PLAY = `<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7-11-7Z"/></svg>`;
const ICON_CLOCK = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 3"/></svg>`;
const ICON_CALENDAR = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/></svg>`;
const ICON_GLOBE = `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 2.5 15.5 0 18M12 3c-2.5 2.5-2.5 15.5 0 18"/></svg>`;

function renderLogo(el) {
  el.innerHTML = `<img src="assets/logo.png" alt="WealthLink Media" class="logo-img">`;
}

// ---------- Video testimonial cards ----------
function videoCardHTML(t) {
  return `
    <div class="testimonial-item">
      <div class="video-card" data-video-src="${t.videoSrc || ""}" data-poster="${t.poster || ""}">
        ${t.poster ? `<img src="${t.poster}" alt="${t.name} testimonial" loading="lazy">` : ""}
        <div class="play-btn">${ICON_PLAY}</div>
        <div class="sound-hint">Click for sound</div>
        ${!t.videoSrc ? `<div class="video-placeholder-label">Video not configured — see testimonials-data.js</div>` : ""}
      </div>
      <p class="testimonial-quote">"${t.quote}"</p>
      <p class="testimonial-attribution">${t.name} with ${t.company}</p>
    </div>
  `;
}

function renderTestimonials(containerId, ids) {
  const el = document.getElementById(containerId);
  if (!el) return;
  const items = ids.map((id) => window.TESTIMONIALS.find((t) => t.id === id)).filter(Boolean);
  el.innerHTML = items.map(videoCardHTML).join("");
  el.classList.add("testimonial-grid");
  wireVideoCards(el);
}

function renderClosingTestimonial(containerId) {
  const el = document.getElementById(containerId);
  if (!el || !window.CLOSING_TESTIMONIAL) return;
  const c = window.CLOSING_TESTIMONIAL;
  el.innerHTML = `
    <p class="testimonial-quote">"${c.quote}"</p>
    <p class="testimonial-attribution">${c.name} with ${c.company}</p>
  `;
}

// ---------- Video playback: hover to preview, click to commit ----------
// Autoplay policy: Chrome/Safari refuse play() with sound until the visitor
// has produced a qualifying gesture on the page - and hovering is NOT one.
// So the first hover on a cold page load can only be muted. We flip this flag
// on the first real pointerdown anywhere, after which unmuted hover playback
// is allowed and works. Before that we attempt sound anyway (a returning
// visitor with a high Media Engagement Index is allowed it outright) and fall
// back to muted + a "tap for sound" badge if the promise rejects.
let audioUnlocked = false;
document.addEventListener("pointerdown", () => { audioUnlocked = true; }, { capture: true, once: true });

function canHoverPlay() {
  return window.matchMedia("(hover: hover) and (pointer: fine)").matches;
}

// The <video> is built once per card on first use and then kept, layered over
// the poster <img> rather than replacing it - so leaving and re-entering the
// card doesn't re-download the file, and the poster is still there to fade
// back to.
function buildCardVideo(card) {
  if (card._video) return card._video;
  const src = card.dataset.videoSrc;
  if (!src) return null;
  const v = document.createElement("video");
  v.src = src;
  v.className = "hover-video";
  v.playsInline = true;
  v.preload = "metadata";
  v.addEventListener("ended", () => releaseCard(card));
  card.appendChild(v);
  card._video = v;
  return v;
}

// Stop a preview and fade the poster back in. A card the user actually
// clicked ("committed") is left alone - that one keeps playing.
function releaseCard(card) {
  const v = card._video;
  if (!v) return;
  v.pause();
  try { v.currentTime = 0; } catch (e) {}
  v.controls = false;
  card.classList.remove("is-previewing", "is-committed", "is-muted");
}

function stopOtherVideos(except) {
  document.querySelectorAll(".video-card.is-previewing").forEach((c) => {
    if (c !== except) releaseCard(c);
  });
}

function playCard(card, committed) {
  const v = buildCardVideo(card);
  if (!v) {
    console.warn("[RankFlow] No video source set for this testimonial yet.");
    return;
  }
  stopOtherVideos(card);           // only ever one playing at a time
  card.classList.add("is-previewing");
  card.classList.toggle("is-committed", !!committed);
  v.controls = !!committed;
  v.muted = false;
  v.volume = 1;
  card.classList.remove("is-muted");

  const p = v.play();
  if (p && p.catch) {
    p.catch(() => {
      // Blocked for sound - retry muted so the visitor still sees something.
      v.muted = true;
      card.classList.add("is-muted");
      v.play().catch(() => {});
    });
  }
}

function wireVideoCards(scopeEl, opts) {
  const hoverEnabled = !opts || opts.hoverPreview !== false;
  (scopeEl || document).querySelectorAll(".video-card").forEach((card) => {
    if (card.dataset.wiredVideo) return;
    card.dataset.wiredVideo = "1";

    if (hoverEnabled) {
      // Small delay so dragging the cursor across the row doesn't fire off
      // three downloads and three bursts of audio.
      card.addEventListener("mouseenter", () => {
        if (!canHoverPlay()) return;
        if (card.classList.contains("is-committed")) return;
        clearTimeout(card._hoverT);
        card._hoverT = setTimeout(() => playCard(card, false), 140);
      });
      card.addEventListener("mouseleave", () => {
        clearTimeout(card._hoverT);
        if (card.classList.contains("is-committed")) return;
        releaseCard(card);
      });
    }

    card.addEventListener("click", function () {
      // Once committed, the native controls live inside this same element and
      // their clicks bubble up here. Bailing out is what keeps pause, seek and
      // fullscreen from being hijacked and restarting the video.
      if (card.classList.contains("is-committed")) return;
      playCard(card, true);
    });
  });
}

function renderExplainerVideo(containerId, stepBarId) {
  const el = document.getElementById(containerId);
  if (!el || !window.EXPLAINER_VIDEO) return;
  const v = window.EXPLAINER_VIDEO;
  const stepBar = stepBarId ? document.getElementById(stepBarId) : null;
  if (!v.videoSrc) {
    // Nothing configured yet - don't show a broken-looking placeholder box
    // (or a "Step 1: Watch This Video" header with nothing under it), just
    // don't render this section at all until a real video is set.
    el.innerHTML = "";
    if (stepBar) stepBar.style.display = "none";
    return;
  }
  el.innerHTML = `
    <div class="explainer-video-wrap">
      <div class="video-card" data-video-src="${v.videoSrc}" data-poster="${v.poster || ""}" style="aspect-ratio:16/9;max-height:none;">
        ${v.poster ? `<img src="${v.poster}" alt="Explainer video" loading="lazy">` : ""}
        <div class="play-btn">${ICON_PLAY}</div>
      </div>
      <div class="explainer-caption">${v.caption || ""}</div>
    </div>
  `;
  // Click-only: hover-starting a 2-minute explainer with audio every time the
  // cursor crosses it would be obnoxious. Testimonial cards opt in instead.
  wireVideoCards(el, { hoverPreview: false });
}

// ---------- Lead routing ----------
// Confirmed routing rules:
//   GBP = No                                -> sorry (any revenue)
//   Revenue $0-10k                          -> sorry (any qualifying GBP)
//   GBP = Yes AND revenue $25k+             -> tracked (main) calendar, Lead pixel fires
//   everything else that isn't disqualified -> untracked calendar, no pixel
//     (GBP = unverified/suspended at any qualifying revenue, or
//      GBP = Yes with revenue $10-25k)
function routeUser(gbp, revenue) {
  if (gbp === "no") return "no-google-business.html";   // ← was "sorry.html"
  if (revenue === "r0_10") return "sorry.html";
  if (gbp === "yes" && (revenue === "r25_100" || revenue === "r100plus")) {
    return "book-tracked.html";
  }
  return "book-untracked.html";
}

function getLeadFirstName() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("fn")) return params.get("fn");
  try {
    const stored = JSON.parse(sessionStorage.getItem("rankflow_lead") || "{}");
    return stored.firstName || "";
  } catch (e) {
    return "";
  }
}

// Which steps are on screen, given the Google Business Page answer.
// Business name is now the ONLY conditional field - everything else,
// phone included, is visible from the moment the modal opens.
//   Yes / Unverified -> business name shown
//   No / nothing yet -> business name hidden
function visibleSteps(gbp) {
  if (gbp === "yes" || gbp === "unverified") {
    return ["firstName", "gbp", "businessName", "phone", "revenue", "submit"];
  }
  return ["firstName", "gbp", "phone", "revenue", "submit"];
}

function digitsOnly(v) {
  return String(v || "").replace(/\D/g, "");
}

function wireProgressiveForm(formEl) {
  if (!formEl) return;
  const steps = {};
  formEl.querySelectorAll("[data-step]").forEach((f) => { steps[f.dataset.step] = f; });
  const bar = formEl.querySelector(".form-progress i");

  function gbpValue() {
    const c = formEl.querySelector('[name="gbp"]:checked');
    return c ? c.value : "";
  }

  function isComplete(name) {
    switch (name) {
      case "firstName":    return formEl.firstName.value.trim().length >= 2;
      case "gbp":          return !!gbpValue();
      case "businessName": return formEl.businessName.value.trim().length >= 3;
      case "phone":        return digitsOnly(formEl.phone.value).length >= 10;
      case "revenue":      return !!formEl.querySelector('[name="revenue"]:checked');
      default:             return true;
    }
  }

  function setVisible(field, show) {
    const wasHidden = field.classList.contains("is-hidden");
    if (show) {
      field.classList.remove("is-hidden");
      clearTimeout(field._openT);
      // Overflow stays clipped while the height animates, otherwise the
      // expanding box can't be transitioned cleanly. Once it's done we let
      // overflow go visible again so the Places dropdown isn't cut off by
      // its own parent.
      field._openT = setTimeout(() => field.classList.add("is-open"), 400);
       if (wasHidden) {
        field.classList.remove("just-revealed");
        void field.offsetWidth;              // forces the animation to restart
        field.classList.add("just-revealed");
        setTimeout(() => field.scrollIntoView({ behavior: "smooth", block: "nearest" }), 280);
      }
    } else {
      clearTimeout(field._openT);
      field.classList.add("is-hidden");
      field.classList.remove("is-open");
    }
  }

  function clearField(field) {
    field.querySelectorAll("input").forEach((i) => {
      if (i.type === "radio" || i.type === "checkbox") i.checked = false;
      else i.value = "";
    });
    field.classList.remove("is-done", "has-error");
    const w = field.querySelector(".autocomplete-wrapper");
    if (w) w.classList.remove("is-picked");
  }

  function update() {
    const path = visibleSteps(gbpValue());

    Object.keys(steps).forEach((name) => {
      const f = steps[name];
      const shouldShow = path.indexOf(name) !== -1;
      const wasShowing = !f.classList.contains("is-hidden");

      setVisible(f, shouldShow);

      // Wipe a field on its way out so a stale value never reaches
      // sessionStorage or the webhook — e.g. a business name typed under
      // "Yes" before switching to "No".
      if (!shouldShow && wasShowing) clearField(f);

      if (shouldShow) {
        const done = isComplete(name);
        f.classList.toggle("is-done", done && name !== "submit");
        if (done) f.classList.remove("has-error");
      }
    });

    if (bar) {
      const req = path.filter((n) => n !== "submit");
      const filled = req.filter(isComplete).length;
      bar.style.width = Math.round((filled / req.length) * 100) + "%";
    }
  }


  // Live phone formatting -> (555) 123-4567
  if (formEl.phone) {
    formEl.phone.addEventListener("input", function () {
      const d = digitsOnly(this.value).slice(0, 10);
      this.value = d.length > 6 ? `(${d.slice(0, 3)}) ${d.slice(3, 6)}-${d.slice(6)}`
                 : d.length > 3 ? `(${d.slice(0, 3)}) ${d.slice(3)}`
                 : d.length > 0 ? `(${d}`
                 : "";
    });
  }

  formEl.addEventListener("input", update);
  formEl.addEventListener("change", update);
  formEl.__update = update;   // wireModal() calls this on open to re-sync
  update();
}

// ---------- Lead form: validation, storage, routing ----------
// The form carries `novalidate` and the inputs have no `required` attribute:
// a hidden field that is still `required` makes Chrome refuse to submit with
// "An invalid form control is not focusable", so validation happens here
// instead, against whichever path the user is actually on.
function wireLeadForm(formEl) {
  if (!formEl) return;
  formEl.addEventListener("submit", function (e) {
    e.preventDefault();
    const gbp = (formEl.querySelector('[name="gbp"]:checked') || {}).value;
    const needsBusiness = gbp === "yes" || gbp === "unverified";

    const data = {
      firstName: formEl.firstName.value.trim(),
      phone: formEl.phone.value.trim(),
      gbp: gbp,
      businessName: needsBusiness ? formEl.businessName.value.trim() : "",
      businessPlaceId: needsBusiness ? formEl.placeId.value : "",
      businessAddress: needsBusiness ? formEl.placeAddress.value : "",
      revenue: (formEl.querySelector('[name="revenue"]:checked') || {}).value,
    };

    const missing = [];
    if (data.firstName.length < 2) missing.push("firstName");
    if (!data.gbp) missing.push("gbp");
    if (needsBusiness && data.businessName.length < 3) missing.push("businessName");
    if (digitsOnly(data.phone).length < 10) missing.push("phone");
    if (!data.revenue) missing.push("revenue");
    if (missing.length) {
      const f = formEl.querySelector('[data-step="' + missing[0] + '"]');
      if (f) {
        f.classList.add("has-error");
        f.scrollIntoView({ behavior: "smooth", block: "center" });
        const inp = f.querySelector("input");
        if (inp) inp.focus();
      }
      return;
    }

    sessionStorage.setItem("rankflow_lead", JSON.stringify(data));
    if (window.RANKFLOW_CONFIG.LEAD_WEBHOOK_URL) {
      fetch(window.RANKFLOW_CONFIG.LEAD_WEBHOOK_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
        keepalive: true,
      }).catch(() => {});
    }
    const dest = routeUser(data.gbp, data.revenue);
    window.location.href = dest + "?fn=" + encodeURIComponent(data.firstName);
  });
}

// ---------- Google Places: custom-rendered autocomplete ----------
// Google's stock Autocomplete widget injects its own unstyleable .pac-container
// dropdown, so instead we call the suggestions service directly and render our
// own list. Tries the new AutocompleteSuggestion API first and falls back to
// the legacy AutocompleteService if the key/project only has the old one.
let placesLoading = null;
function loadGooglePlaces() {
  if (placesLoading) return placesLoading;
  placesLoading = new Promise((resolve) => {
    const key = window.RANKFLOW_CONFIG.GOOGLE_PLACES_API_KEY;
    if (!key || key.startsWith("REPLACE")) {
      console.warn("[RankFlow] GOOGLE_PLACES_API_KEY not configured — business autocomplete disabled (field still works as plain text).");
      resolve(false);
      return;
    }
    if (window.google && window.google.maps && window.google.maps.places) {
      resolve(true);
      return;
    }
    const script = document.createElement("script");
    script.src = "https://maps.googleapis.com/maps/api/js?key=" +
      encodeURIComponent(key) + "&libraries=places&loading=async&v=weekly";
    script.async = true;
    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);
    document.head.appendChild(script);
  });
  return placesLoading;
}

function fetchPlaceSuggestions(query) {
  const places = window.google && window.google.maps && window.google.maps.places;
  if (!places) return Promise.resolve([]);

  // Places API (New)
  if (places.AutocompleteSuggestion) {
    return places.AutocompleteSuggestion.fetchAutocompleteSuggestions({
      input: query,
      includedPrimaryTypes: ["establishment"],
      includedRegionCodes: ["us"],
    }).then((res) => (res.suggestions || []).map((s) => {
      const p = s.placePrediction;
      return {
        id: p.placeId,
        name: p.mainText ? p.mainText.text : p.text.text,
        address: p.secondaryText ? p.secondaryText.text : "",
      };
    })).catch((err) => {
      console.warn("[RankFlow] Places lookup failed:", err);
      return [];
    });
  }

  // Legacy fallback
  return new Promise((resolve) => {
    new places.AutocompleteService().getPlacePredictions(
      { input: query, types: ["establishment"], componentRestrictions: { country: "us" } },
      (preds, status) => {
        if (status !== places.PlacesServiceStatus.OK || !preds) return resolve([]);
        resolve(preds.map((p) => ({
          id: p.place_id,
          name: p.structured_formatting ? p.structured_formatting.main_text : p.description,
          address: p.structured_formatting ? (p.structured_formatting.secondary_text || "") : "",
        })));
      }
    );
  });
}

function escHtml(s) {
  return String(s || "").replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

function wireBusinessAutocomplete(inputEl) {
  const wrap = inputEl.closest(".autocomplete-wrapper");
  if (!wrap) return;
  const list = wrap.querySelector(".ac-suggestions");
  const spinner = wrap.querySelector(".ac-spinner");
  const form = inputEl.form;
  const placeIdEl = form.querySelector('[name="placeId"]');
  const placeAddrEl = form.querySelector('[name="placeAddress"]');

  let items = [], active = -1, timer = null, seq = 0, apiReady = false, suppress = false;

  loadGooglePlaces().then((ok) => { apiReady = ok; });

  function close() {
    list.hidden = true;
    list.innerHTML = "";
    items = [];
    active = -1;
    inputEl.setAttribute("aria-expanded", "false");
  }

  function render() {
    if (!items.length) return close();
    list.innerHTML = items.map((it, i) =>
      `<li class="ac-item${i === active ? " active" : ""}" role="option" data-i="${i}">
         ${ICON_PIN}
         <span class="ac-text">
           <span class="ac-name">${escHtml(it.name)}</span>
           <span class="ac-addr">${escHtml(it.address)}</span>
         </span>
       </li>`).join("");
    list.hidden = false;
    inputEl.setAttribute("aria-expanded", "true");
  }

  function choose(i) {
    const it = items[i];
    if (!it) return;
    suppress = true;
    inputEl.value = it.name;
    if (placeIdEl) placeIdEl.value = it.id || "";
    if (placeAddrEl) placeAddrEl.value = it.address || "";
    wrap.classList.add("is-picked");
    close();
    suppress = false;
    // Tell the progressive-reveal logic the field is filled, so the phone
    // step unlocks on pick without the user typing another character.
    inputEl.dispatchEvent(new Event("input", { bubbles: true }));
  }

  inputEl.addEventListener("input", function () {
    if (suppress) return;
    // Typing after a pick invalidates that pick.
    wrap.classList.remove("is-picked");
    if (placeIdEl) placeIdEl.value = "";
    if (placeAddrEl) placeAddrEl.value = "";

    const q = inputEl.value.trim();
    clearTimeout(timer);
    if (!apiReady || q.length < 3) { close(); spinner.hidden = true; return; }

    spinner.hidden = false;
    timer = setTimeout(() => {
      const my = ++seq;
      fetchPlaceSuggestions(q).then((res) => {
        if (my !== seq) return;          // a newer keystroke already won
        spinner.hidden = true;
        items = res.slice(0, 6);
        active = -1;
        render();
      });
    }, 220);
  });

  inputEl.addEventListener("keydown", (e) => {
    if (list.hidden) return;
    if (e.key === "ArrowDown") { e.preventDefault(); active = (active + 1) % items.length; render(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); active = (active - 1 + items.length) % items.length; render(); }
    else if (e.key === "Enter" && active > -1) { e.preventDefault(); choose(active); }
    else if (e.key === "Escape") { close(); }
  });

  // mousedown, not click - blur would tear the list down before click lands
  list.addEventListener("mousedown", (e) => {
    const li = e.target.closest(".ac-item");
    if (!li) return;
    e.preventDefault();
    choose(Number(li.dataset.i));
  });

  inputEl.addEventListener("blur", () => setTimeout(close, 120));
}

// ---------- GHL calendar, lazy-loaded after page is idle ----------
// GHL's own embed snippet is: an iframe (id = the widget ID from the booking
// URL) + a single <script src=".../form_embed.js"> that listens for
// postMessage from the iframe to auto-resize it (GHL calendars are variable
// height depending on the booking step). We inject both, lazily.
let ghlEmbedScriptLoaded = false;
function ensureGhlEmbedScript() {
  if (ghlEmbedScriptLoaded) return;
  ghlEmbedScriptLoaded = true;
  const s = document.createElement("script");
  s.src = "https://link.msgsndr.com/js/form_embed.js";
  document.body.appendChild(s);
}

function loadGhlCalendar(containerId, url) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (!url || url.startsWith("REPLACE")) {
    container.innerHTML = '<p class="calendar-loading">Calendar not configured yet — see config.js</p>';
    return;
  }
  const widgetId = url.split("/").filter(Boolean).pop();
  const run = () => {
    const iframe = document.createElement("iframe");
    iframe.src = url;
    iframe.id = widgetId;
    iframe.setAttribute("allow", "payment");
    iframe.setAttribute("scrolling", "no");
    iframe.style.width = "100%";
    iframe.style.minHeight = "750px";
    iframe.style.border = "none";
    iframe.style.overflow = "hidden";
    iframe.loading = "lazy";
    container.innerHTML = "";
    container.appendChild(iframe);
    ensureGhlEmbedScript();
  };
  if (document.readyState === "complete") {
    "requestIdleCallback" in window ? requestIdleCallback(run) : setTimeout(run, 200);
  } else {
    window.addEventListener("load", () => {
      "requestIdleCallback" in window ? requestIdleCallback(run) : setTimeout(run, 200);
    });
  }
}

// ---------- Sticky bottom CTA bar: appears on scroll-down, hides on
// scroll-up (and stays hidden near the top, since the hero button is
// already visible there) ----------
function wireStickyCta(barId) {
  const bar = document.getElementById(barId);
  if (!bar) return;
  let lastY = window.scrollY;
  let ticking = false;
  function onScroll() {
    const y = window.scrollY;
    if (y < 80) {
      bar.classList.remove("visible");
    } else if (y > lastY) {
      bar.classList.add("visible");
    } else {
      bar.classList.remove("visible");
    }
    lastY = y;
    ticking = false;
  }
  window.addEventListener("scroll", () => {
    if (!ticking) {
      requestAnimationFrame(onScroll);
      ticking = true;
    }
  }, { passive: true });
}

// ---------- Modal open/close ----------
function wireModal(openBtnSelector, overlayId) {
  const overlay = document.getElementById(overlayId);
  if (!overlay) return;
  document.querySelectorAll(openBtnSelector).forEach((btn) => {
    btn.addEventListener("click", () => {
      overlay.classList.add("open");
      const input = overlay.querySelector('[name="businessName"]');
      if (input && !input.dataset.wired) {
        input.dataset.wired = "1";
        wireBusinessAutocomplete(input);
      }
      // Re-sync which steps are revealed every time the modal opens.
      const f = overlay.querySelector("form");
      if (f && f.__update) f.__update();
    });
  });
  overlay.querySelectorAll("[data-close-modal]").forEach((el) => {
    el.addEventListener("click", () => overlay.classList.remove("open"));
  });
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) overlay.classList.remove("open");
  });
}