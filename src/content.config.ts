import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

// Podcasts — one Markdown file per episode. Deliberately the same shape
// as the Ranked Games repo's `games` collection: plain frontmatter,
// nothing computed, nothing that needs syncing.
const podcasts = defineCollection({
  loader: glob({ pattern: "*.md", base: "./src/content/podcasts" }),
  schema: z.object({
    title: z.string(),
    publishDate: z.string(), // YYYY-MM-DD, shown as-is
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
  }),
});

export const collections = { podcasts, gallery };
