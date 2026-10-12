import { getCollection } from "astro:content";

// Published reviews, newest first. Drafts (draft: true) are left out
// everywhere: no page, no listing.
export async function getReviews() {
  return (await getCollection("reviews", ({ data }) => !data.draft)).sort((a, b) =>
    b.data.publishDate.localeCompare(a.data.publishDate)
  );
}

// "2026-10-10" -> "October 10, 2026". Parsed by hand so the server's
// time zone can never shift it to the day before.
export function formatReviewDate(ymd: string): string {
  // publishDate may carry a time ("2026-10-11 14:00") to order two reviews
  // posted the same day; only the date part is shown.
  const [y, m, d] = ymd.slice(0, 10).split("-").map(Number);
  const months = ["January", "February", "March", "April", "May", "June", "July",
    "August", "September", "October", "November", "December"];
  return m && d ? `${months[m - 1]} ${d}, ${y}` : ymd;
}

// A YouTube watch/short/youtu.be link -> its embed URL, or null.
export function youtubeEmbed(url?: string): string | null {
  if (!url) return null;
  const m = url.match(/(?:youtu\.be\/|v=|shorts\/|embed\/)([A-Za-z0-9_-]{11})/);
  return m ? `https://www.youtube-nocookie.com/embed/${m[1]}` : null;
}
