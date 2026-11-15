// Finds a cover image for a game by id, at build time. Looks for
// public/<folder>/<id>.(jpg|jpeg|png|webp) and returns its URL, or null so
// the page can show a title card instead. Replacing a cover is just
// dropping a correctly-named file into that folder and pushing.
//
// listGameExtras() returns any additional pictures for one game: every image
// inside public/images/<folder>/<id>/ (a sub-folder named exactly like the
// game's id), in natural filename order. No folder = no gallery.
import fs from "node:fs";
import path from "node:path";
import { withBase } from "./site";

const EXTENSIONS = ["jpg", "jpeg", "png", "webp"];

export function findGameArt(folder: string, id: string): string | null {
  const dir = path.join(process.cwd(), "public", "images", folder);
  for (const ext of EXTENSIONS) {
    if (fs.existsSync(path.join(dir, `${id}.${ext}`))) {
      return withBase(`/images/${folder}/${id}.${ext}`);
    }
  }
  return null;
}

export function listGameExtras(folder: string, id: string): string[] {
  const dir = path.join(process.cwd(), "public", "images", folder, id);
  if (!fs.existsSync(dir) || !fs.statSync(dir).isDirectory()) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => [...EXTENSIONS, "gif", "svg"].includes(f.split(".").pop()!.toLowerCase()))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    .map((f) => withBase(`/images/${folder}/${id}/${encodeURIComponent(f)}`));
}
