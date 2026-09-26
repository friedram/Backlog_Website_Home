import { parse } from "yaml";
import raw from "../content/activity.yaml?raw";

export interface ActivityEntry {
  text: string;
  date: string;
}

/**
 * The only place activity.yaml is read. Imported as a raw string at
 * build time (Vite's `?raw`), same reasoning as the Ranked Games repo's
 * ranking.ts: Astro relocates prerendered chunks during build, which
 * breaks any filesystem path relative to the source tree at render time.
 */
export function getActivity(): ActivityEntry[] {
  const parsed = parse(raw);
  return Array.isArray(parsed) ? parsed : [];
}
