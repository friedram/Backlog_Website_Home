// Same helper, same reasoning, as the Ranked Games repo's src/lib/site.ts:
// this site also deploys into a subfolder of deathbybacklog.com (see
// astro.config.mjs), so every root-relative internal link/image path has
// to go through this instead of a bare string, or it'll point at the
// wrong place once deployed.
export function withBase(path: string): string {
  const base = import.meta.env.BASE_URL.replace(/\/$/, "");
  const p = path.startsWith("/") ? path : `/${path}`;
  return base + p;
}

// Gallery entries can point at either a local file under
// public/images/gallery/ (a bare filename) or a live WordPress media URL
// (Andy's existing /other/images/ library — see site-redesign-proposal.md's
// note on hotlinking rather than duplicating those photos into this repo).
// This is the one place that decides which, so components don't each
// re-implement the http(s) check.
export function galleryImageSrc(image: string): string {
  return /^https?:\/\//.test(image) ? image : withBase(`/images/gallery/${image}`);
}
