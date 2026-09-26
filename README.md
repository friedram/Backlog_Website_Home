# Backlog_Website_Home

The redesigned Home page for [deathbybacklog.com](https://deathbybacklog.com) — the first page built from `site-redesign-proposal.md`. A separate Astro repo from Ranked Games, on purpose (Andy's call, 2026-09-24): ship pages one at a time without touching WordPress or reopening the architecture discussion. Whether this eventually merges into one codebase with Ranked Games is a later decision — see `architecture-migration-plan.md` in the project, not this repo.

## What's here

- **The rotating hero** — full-bleed, edge to edge under the header (not a bordered card), built from Collection Gallery entries flagged `hero: true`. Currently 5 real photos: Andy's own shelf photo plus 4 hotlinked straight from the live WordPress `/other/images/` media library (StarCraft figures, the custom arcade cabinet, a collector's-editions close-up, and a retro/PC shelf).
- **The dashboard** — Featured Ranked Game, Latest Podcast, Featured Gallery Image, Recent Activity, in a 2x2 grid.
- **Currently Climbing** — the top of the live ranking, teasing the full Ranked Games page.

## Where gallery photos live

`src/content/gallery/*.md`'s `image` field takes either a bare filename (a photo copied into `public/images/gallery/`, like `collection-shelves.jpg`) or a full `https://` URL hotlinked from WordPress's existing media library — `galleryImageSrc()` in `src/lib/site.ts` picks based on which. Hotlinking is the default for real photos now: WordPress stays up as the media host, so there's no reason to duplicate ~30 photos into this repo just to display them. The 5 current hero photos are hand-picked, not all ~27 in the library — `hero: true` is deliberately a curated subset (see the comment in `content.config.ts`), the same way the ranking itself is hand-curated rather than auto-generated.

A future option, not built yet: fetch the WordPress media library automatically at build time (REST API or the `/other/images/` page itself) instead of hand-picking URLs. Worth it once there are new photos often enough that manual curation gets tedious — not before.

## How it reuses the Ranked Games design system

`src/styles/tokens.css` is copied verbatim from the Ranked Games repo — same colors, type, hero-panel, countdown-row, movement-pill. `src/components/RankBadge.astro` is copied verbatim too (it only ever takes plain numbers, so it works unmodified here). `src/layouts/BaseLayout.astro` follows the same structural pattern as the Ranked Games repo's own layout, extended with the full confirmed nav order:

Home · Podcasts · Ranked Games · ID@Xbox · About · Other · Users

"Home" links to this site's own root; every other item still points at the live WordPress pages, exactly the way the Ranked Games repo's nav already does. Other and Users are plain links for now, not dropdowns — each currently has exactly one sub-page (Images, GruffyGrey), so a dropdown menu doesn't earn its complexity yet. Worth adding once those pages get rebuilt and actually have more than one child each.

## The one cross-repo dependency: the ranked-games feed

"Featured Ranked Game" and "Currently Climbing" need live ranking data, but this repo deliberately does **not** duplicate the `games` collection or `ranking.yaml` — that would recreate the exact parallel-value-sync problem those files were designed to avoid, one repo further out.

Instead, `src/lib/rankedFeed.ts` fetches a small JSON feed at *this repo's* build time from:

```
https://deathbybacklog.com/ranked-games/home-feed.json
```

That file is published by the **Ranked Games repo**, not this one — see the `home-feed.json.ts` endpoint added there alongside this repo. Ranked Games stays the single source of truth; this repo just reads its own published output, the same way a browser would.

**Sequencing matters**: the Ranked Games repo's change needs to be merged and deployed *before* this repo's first build will show real data. Until then, the fetch fails soft (a console warning, not a build failure) and the page renders its honest empty-state ("Nothing to show yet").

## What still needs real content before this goes live

- **Gallery: one real photo in, two placeholders left.** `src/content/gallery/shelf-01.md` uses a real shelf photo Andy provided directly (`public/images/gallery/collection-shelves.jpg`, exif-corrected and resized to 1600px). `placeholder-collectors-edition.md` and `placeholder-setup.md` are still SVG placeholders. The remaining real photos (WordPress's `/other/images/` media library, ~30 photos) need to be exported and dropped into `public/images/gallery/`, with a `.md` entry each — not something I can source myself, no access to that media library from here.
- **Podcast entries**: only Episode 0 is seeded (real data, pulled from the live site). Add more `.md` files to `src/content/podcasts/` as episodes come out.
- **Activity log**: seeded with two real entries. Add a new line at the top of `src/content/activity.yaml` whenever something worth mentioning happens.

## Deploying

Same pipeline as Ranked Games: push to `main`, GitHub Actions builds and deploys over FTPS. This repo needs its own three secrets set in GitHub (Settings → Secrets and variables → Actions), same names as the Ranked Games repo:

- `HOSTINGER_SFTP_HOST`
- `HOSTINGER_SFTP_USERNAME`
- `HOSTINGER_SFTP_PASSWORD`

Deploys to `/domains/deathbybacklog.com/public_html/home-preview/` — visible at `deathbybacklog.com/home-preview/` once it's live. That's a deliberate staging path, not the final one: WordPress still serves the real `/` while this is under review. Promoting this to the actual homepage later is a `base` config change (`/home-preview` → `/`) plus a `server-dir` change in `deploy.yml` — a deploy-target change, not a rebuild.

## Local development

```
npm install
npm run dev
```
