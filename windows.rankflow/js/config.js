// ============================================================
// RankFlow Funnel — Configuration
// Fill in every REPLACE_WITH_* value below before going live.
// Nothing else in the codebase needs to change once these are set.
// ============================================================
window.RANKFLOW_CONFIG = {
  // Meta (Facebook) Pixel ID — Events Manager > Data Sources > your pixel.
  META_PIXEL_ID: "4390908821128639",

  // Google Places API key, restricted to the Maps JavaScript API (Places
  // library) and to this domain. console.cloud.google.com > APIs & Services.
  GOOGLE_PLACES_API_KEY: "AIzaSyB7VqEv9lQC71rLQmLlH2JOp9WSyhf9aTk",

  // GHL calendar embed URLs (GHL: Calendars > [calendar] > Embed > copy the
  // iframe src). TRACKED = the "main" calendar (25k+ revenue AND verified
  // GBP). UNTRACKED = everyone else who still qualifies (unverified/suspended
  // GBP at any qualifying revenue, or 10-25k revenue with a verified GBP).
  GHL_CALENDAR_TRACKED_URL: "https://api.leadconnectorhq.com/widget/booking/RLJBIDoVL2gvxpqqI7lu",
  GHL_CALENDAR_UNTRACKED_URL: "https://api.leadconnectorhq.com/widget/booking/sCFZ3xO5KSrolIiIe0FY",

  // GHL inbound webhook. The qualifying-form answers are POSTed here the
  // instant the form is submitted, so the lead lands in GHL even if they
  // never make it to the calendar. Set up in GHL under
  // Automation > Workflows > trigger: Inbound Webhook.
  LEAD_WEBHOOK_URL: "https://services.leadconnectorhq.com/hooks/oJyfQVqrbosEEz3hI106/webhook-trigger/OZeOXTw3DmP0oqwtCIOH",
};
