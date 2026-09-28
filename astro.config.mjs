import { defineConfig } from "astro/config";

// Promoted to the real domain root on 2026-09-28. Previously lived at
// /home-preview/ as a review copy while WordPress still owned "/" — see
// git history for that version. WordPress's other pages (About, Podcasts,
// Other/Images, Users, ID@Xbox) are untouched and keep working exactly
// as before; only "/" itself now resolves to this build, via one small
// addition to the shared .htaccess (see architecture-migration-plan.md).
// The pre-promotion homepage is preserved as a frozen static snapshot at
// deathbybacklog.com/old-home/, completely independent of this repo.
export default defineConfig({
  output: "static",
  site: "https://deathbybacklog.com",
  base: "/",
});
