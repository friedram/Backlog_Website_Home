// Home needs to show live ranking data (the "Currently Climbing" strip
// and the "Featured Ranked Game" dashboard tile) without duplicating the
// games collection or ranking.yaml into this repo — that would recreate
// exactly the parallel-value-sync problem those files were designed to
// avoid, just one repo further out.
//
// Instead, this repo consumes a small JSON feed that the Ranked Games
// repo itself publishes at build time (src/pages/home-feed.json.ts over
// there). Ranked Games stays the single source of truth; this is just
// reading its own published output, the same way a browser would.
//
// Fetched once, at THIS repo's build time (not per-request — this is a
// static site). If the feed isn't reachable yet — e.g. this repo is
// built before the Ranked Games repo has shipped its home-feed.json.ts —
// this fails soft: log a warning and return an empty list, so a
// temporary feed outage never breaks the Home build. The page itself
// already has a "nothing ranked yet" fallback for an empty list.
const FEED_URL = "https://deathbybacklog.com/ranked-games/home-feed.json";

export interface FeedGame {
  id: string;
  title: string;
  rank: number;
  previousRank: number | null;
  boxArtUrl: string;
  platform: string[];
  releaseYear: number;
  genre: string[];
  href: string;
}

export async function getRankedFeed(): Promise<FeedGame[]> {
  try {
    const res = await fetch(FEED_URL);
    if (!res.ok) {
      console.warn(`[rankedFeed] ${FEED_URL} returned ${res.status} — rendering with an empty feed.`);
      return [];
    }
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (err) {
    console.warn(`[rankedFeed] Could not fetch ${FEED_URL} — rendering with an empty feed.`, err);
    return [];
  }
}
