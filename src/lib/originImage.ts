// "Your Origin" image slots — lets the page owner pick their own pictures
// without editing any code. This is a static site, so "upload" means:
// drop a file into the folder below and push. At build time this looks for
//
//   public/images/users/<user>/xbox-25/origin/left.(png|jpg|jpeg|webp|svg|gif)
//   public/images/users/<user>/xbox-25/origin/right.(png|jpg|jpeg|webp|svg|gif)
//
//   .../origin/full.(png|jpg|...)   - ONE wide picture that replaces the whole
//                                       graphic (use this for a single combined image)
//
//   .../origin/extra/*.(png|jpg|...) - any number of EXTRA pictures shown
//                                       right under the "Your Origin" heading,
//                                       ABOVE the existing graphic (which stays).
//                                       Shown in filename order (01-, 02-, ...).
//
// "left" is the slot next to "Player Since", "right" the one next to
// "First Console". If a file is there it replaces the default for that slot;
// if not, the page falls back to its built-in default. Delete the file to
// go back to the default.
import fs from "node:fs";
import path from "node:path";
import { withBase } from "./site";

const EXTENSIONS = ["png", "jpg", "jpeg", "webp", "svg", "gif"];

export function findOriginImage(user: string, slot: "left" | "right" | "full"): string | null {
  const dir = path.join(process.cwd(), "public", "images", "users", user, "xbox-25", "origin");
  for (const ext of EXTENSIONS) {
    if (fs.existsSync(path.join(dir, `${slot}.${ext}`))) {
      return withBase(`/images/users/${user}/xbox-25/origin/${slot}.${ext}`);
    }
  }
  return null;
}

// Extra pictures shown immediately under the "Your Origin" heading, in
// filename order. Returns [] when the folder is missing or empty.
export function listOriginExtras(user: string): string[] {
  const dir = path.join(process.cwd(), "public", "images", "users", user, "xbox-25", "origin", "extra");
  if (!fs.existsSync(dir)) return [];
  return fs
    .readdirSync(dir)
    .filter((f) => EXTENSIONS.includes(f.split(".").pop()!.toLowerCase()))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
    .map((f) => withBase(`/images/users/${user}/xbox-25/origin/extra/${encodeURIComponent(f)}`));
}
