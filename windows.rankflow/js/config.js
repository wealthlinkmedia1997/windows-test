// ============================================================
// RankFlow Funnel — Configuration
// Fill in every REPLACE_WITH_* value below before going live.
// Nothing else in the codebase needs to change once these are set.
//
// SECURITY: this file is loaded directly in the browser, so anything
// placed here is public. Do NOT commit real key/secret values to git —
// edit this file with the live values only on the deploy target (server/
// hosting provider), after it has been copied from git. A key committed
// to git history stays compromised even after being removed from HEAD,
// so if a real key ever ends up here in a commit, rotate it in the
// provider's console immediately rather than relying on removing it.
//
// For GOOGLE_PLACES_API_KEY specifically: this must be a browser-type
// key restricted in console.cloud.google.com > APIs & Services >
// Credentials to (a) HTTP referrers = this site's exact domain(s), and
// (b) API restriction = Maps JavaScript API only. That restriction, not
// secrecy, is what makes it safe for the key to be visible client-side.
// ============================================================
window.RANKFLOW_CONFIG = {
  // Meta (Facebook) Pixel ID — Events Manager > Data Sources > your pixel.
  META_PIXEL_ID: "4390908821128639",

  // Google Places API key, restricted to the Maps JavaScript API (Places
  // library) and to this domain. console.cloud.google.com > APIs & Services.
  GOOGLE_PLACES_API_KEY: "REPLACE_WITH_GOOGLE_PLACES_API_KEY",

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
