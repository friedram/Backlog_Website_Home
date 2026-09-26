import { defineConfig } from "astro/config";

// Deployed the same way Ranked Games is: a subfolder of the existing
// deathbybacklog.com WordPress site, over the same GitHub Actions ->
// Hostinger FTPS pipeline. This lives at /home-preview/ for now, on
// purpose — it's a review copy, not the live homepage. WordPress still
// owns "/" while this is being built out. Promoting this to the real
// domain root later (base: "/") is a deliberate, separate step once
// it's approved — a config + deploy-target change, not a rebuild.
export default defineConfig({
  output: "static",
  site: "https://deathbybacklog.com",
  base: "/home-preview",
});
