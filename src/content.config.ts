import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

// Podcasts — one Markdown file per episode. Deliberately the same shape
// as the Ranked Games repo's `games` collection: plain frontmatter,
// nothing computed, nothing that needs syncing.
const podcasts = defineCollection({
  loader: glob({ pattern: "*.md", base: "./src/content/podcasts" }),
  schema: z.object({
    title: z.string(),
    episodeNumber: z.number(), // sort key — the feed is ordered by this, highest first
    // YYYY-MM-DD, shown as-is. Optional: Audiomack's own "Release Date" field
    // turned out to reflect whenever a file was last re-uploaded, not when an
    // episode actually aired (confirmed wrong for at least one older episode),
    // so it's only set here when the real air date is known — from the
    // episode's own title, or told to us directly. Left blank rather than
    // guessing for the rest.
    publishDate: z.string().optional(),
    listenUrl: z.string().url(),
    coverImage: z.string().optional(), // filename under public/images/podcasts/
    summary: z.string().optional(),
  }),
});

// Collection Gallery (formerly the WordPress "Images" page) — Andy's
// physical game collection: shelves, collector's editions, memorabilia,
// the space itself. Two independent flags, not one, because they do
// different jobs: `hero` opts an image into Home's slow-rotating hero
// (a curated subset — the best, most "this is what the site is about"
// shots); `featured` is the single image shown in Home's dashboard tile
// and can point at something different, e.g. whatever's newest.
const gallery = defineCollection({
  loader: glob({ pattern: "*.md", base: "./src/content/gallery" }),
  schema: z.object({
    // Either a bare filename under public/images/gallery/, or a full
    // https:// URL hotlinked straight from WordPress's existing
    // /other/images/ media library — see galleryImageSrc() in lib/site.ts.
    // Hotlinking is the default for real photos: WordPress is staying up
    // as the media host (Andy's decision, 2026-09-24), so there's no need
    // to duplicate ~30 photos into this repo just to show them here.
    image: z.string(),
    caption: z.string().optional(),
    tag: z.string().optional(), // free text, e.g. "shelf", "collector's edition", "setup"
    hero: z.boolean().default(false),
    featured: z.boolean().default(false),
    // How the hero rotator crops this slide's photo. "cover" (default)
    // fills the full-bleed hero frame, cropping edges as needed — right
    // for shelf/room photos where the surroundings don't matter. "contain"
    // shows the whole photo uncropped against a blurred backdrop of the
    // same image — for photos where the whole frame IS the point (a
    // painting, a piece of framed art) and cropping it would lose the
    // thing you're actually showing off. Andy's call, 2026-09-27, for the
    // Halo Museum and Mass Effect office photos specifically.
    fit: z.enum(["cover", "contain"]).default("cover"),
  }),
});

// Reviews (added 2026-10-10) — one Markdown file per review in
// src/content/reviews/<slug>.md; the page lives at /reviews/<slug>/.
// Images go in public/images/reviews/<slug>/. The review text itself is
// the Markdown body; an in-text picture with a caption is a <figure>
// block (see burst-hero.md for the exact pattern to copy).
const reviews = defineCollection({
  loader: glob({ pattern: "*.md", base: "./src/content/reviews" }),
  schema: z.object({
    headline: z.string(), // the review's own title, e.g. "Bullet Heckin'"
    game: z.string(), // the game's name, e.g. "Burst Hero"
    intro: z.string(), // the opening line(s), shown above the key art
    heroImage: z.string(), // filename under public/images/reviews/<slug>/
    heroAlt: z.string().default(""),
    publishDate: z.string(), // YYYY-MM-DD; the Reviews page sorts newest first
    author: z.string().optional(),
    // Platform rule (CONVENTIONS.md): PC and Xbox only, unless the game
    // is on neither; never Sony or Nintendo for a PC/Xbox game.
    platforms: z.array(z.string()).default([]),
    reviewedOn: z.string().optional(), // e.g. "Xbox Series X|S"
    pros: z.string().optional(),
    cons: z.string().optional(),
    recommendation: z.string().optional(),
    runtime: z.string().optional(),
    youtubeUrl: z.string().url().optional(), // a video review, if there is one
    draft: z.boolean().default(false), // true = built nowhere, listed nowhere
  }),
});

export const collections = { podcasts, gallery, reviews };
