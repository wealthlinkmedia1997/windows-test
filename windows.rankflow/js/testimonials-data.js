// ============================================================
// Testimonial content. videoSrc points at self-hosted mp4 files in
// assets/videos/ — no Google Drive dependency, plays as a plain
// <video> tag (see wireVideoCards() in main.js). Files were
// downloaded from Drive and re-compressed with ffmpeg (720p width,
// CRF 26, faststart) - originals were 6-7.5 Mbps / up to 91MB each,
// compressed down to ~230-590 kb/s / 1-8MB each.
// ============================================================
window.TESTIMONIALS = [
  {
    id: "todd",
    quote: "The second you stop spending with Google ads you get no calls... SEO [and AI search] is the way to go for sure - the proof is there for me.",
    name: "Todd",
    company: "Tint Veteran",
    videoSrc: "assets/videos/todd.mp4?v=3",
    poster: "assets/videos/todd-poster.jpg",
  },
  {
    id: "anthony",
    quote: "Even in our slowest months in the winter our phone is STILL ringing every day",
    name: "Anthony",
    company: "Window Tint Solutions Nashville TN",
    videoSrc: "assets/videos/anthony.mp4?v=3",
    poster: "assets/videos/anthony-poster.jpg",
  },
  {
    id: "paul",
    quote: "Game changer for my business, generated 8 [large] jobs and had our best month ever in a few months",
    name: "Paul",
    company: "Inland NW Windows Couer D'lane ID",
    videoSrc: "assets/videos/paul.mp4?v=3",
    poster: "assets/videos/paul-poster.jpg",
  },
  {
    id: "jim",
    quote: "And literally within 30 days I'm at the top - I've had everyone tell me they could get me there but nobody could get me there",
    name: "Jim",
    company: "Accent Window Coverings Riverside CA",
    videoSrc: "assets/videos/jim.mp4?v=3",
    poster: "assets/videos/jim-poster.jpg",
  },
  {
    id: "trevor",
    quote: "By the time you're 2 or 3 companies in that burned you, your done. For some reason I trusted Andre and he got us number 1. I ONLY do my own jobs now, no subcontracting",
    name: "Trevor",
    company: "Warrior Windows Casa Grande AZ",
    videoSrc: "assets/videos/trevor.mp4?v=3",
    poster: "assets/videos/trevor-poster.jpg",
  },
  {
    id: "mindi",
    quote: "We have our gifts, we need to focus on what we do and marketers need to focus on what they do - in that short amount of time, the growth has been PHENOMENAL",
    name: "Mindi",
    company: "Metro Tinting Shutters and Blinds of Tulsa OK",
    videoSrc: "assets/videos/mindi.mp4?v=3",
    poster: "assets/videos/mindi-poster.jpg",
  },
  {
    id: "chris",
    quote: "2 months ago I wasnt getting calls, now my site presence has gone through the rough [over 100 5 star reviews] and getting calls every day",
    name: "Chris",
    company: "CK's Windows of Idaho Falls",
    videoSrc: "assets/videos/chris.mp4?v=3",
    poster: "assets/videos/chris-poster.jpg",
  },
  {
    id: "natalie",
    quote: "We were working with another company prior and now we see what a horrible job they did because Andre's team has been amazing",
    name: "Natalie",
    company: "Window & Door Repair Champions Irvine CA",
    videoSrc: "assets/videos/natalie.mp4?v=3",
    poster: "assets/videos/natalie-poster.jpg",
  },
  {
    id: "danny",
    quote: "I saw the ad and thought this would be a scammy thing and come to find out people we work with were very professional [2 new leads within one WEEK]",
    name: "Danny",
    company: "Sno King and Junk Removal - Washington",
    videoSrc: "assets/videos/danny.mp4?v=3",
    poster: "assets/videos/danny-poster.jpg",
  },
  {
    // Not currently placed on any page — kept in case you want to bring it back.
    // No local video file downloaded for this one yet.
    id: "bryan",
    quote: "When the economy is bad, people think you need to hold onto your money, what you need to do is fork over as much of it into the RIGHT marketing at this time... these past 2.5 months I have seen a HUGE difference in jobs",
    name: "Bryan",
    company: "Golden State Tinting Las Vegas",
    videoSrc: "",
    poster: "",
  },
];

// Explainer video shown at the top of booking/thank-you pages
// ("Step 1: Watch This 2 Minute Video"). Still a placeholder - once you
// have this file, same pattern: assets/videos/explainer.mp4.
window.EXPLAINER_VIDEO = {
  videoSrc: "assets/videos/2min.mp4?v=1",
  poster: "assets/videos/2min.jpg?v=1",
  caption: "",
};

// Landing page (index.html) hero testimonials, in order
window.HERO_TESTIMONIAL_IDS = ["todd", "anthony", "paul"];
// Booking pages (book-tracked.html + book-untracked.html), "P.S. check out
// what our contractor clients have to say" section, in order
window.BOOKING_TESTIMONIAL_IDS = ["jim", "trevor", "mindi"];
// Thank-you page: Danny first, then everything from the booking pages, then
// Chris and Natalie
window.THANK_YOU_TESTIMONIAL_IDS = ["danny", "jim", "trevor", "mindi", "chris", "natalie"];

// Final single testimonial + "More Testimonials" button, on booking/thank-you pages
window.CLOSING_TESTIMONIAL = {
  quote: "This was the best money ive ever invested, I've spent twice as much money on other advertising companies for getting no leads, Andre and his team has been WONDERFUL",
  name: "Joseph Schmidt",
  company: "Rev Joes",
};
