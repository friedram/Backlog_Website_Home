#!/usr/bin/env python3
"""
Podcast Manager
===============

A small desktop tool for maintaining the Death By Backlog podcast list
WITHOUT needing an AI session for routine edits:

  - Add a new episode (number, title, air date, Audiomack link, cover art)
  - Edit an existing episode, including changing its number (= its place
    in the list) and swapping its cover art
  - Remove an episode
  - Validate the site still builds (`npm run build`)
  - Commit & push the changes to git

It edits the same files a human (or Claude) would edit by hand:
  - src/content/podcasts/episode-<N>.md     (one small file per episode)
  - public/images/podcasts/ep-<N>.webp      (cover art, 480x480 WebP)

Design notes (why it works the way it does):

  - ORDER = EPISODE NUMBER. The Podcasts page (and Home's "Latest
    Podcast" tile) sort by `episodeNumber`, highest first. There is no
    separate ordering file, so "put it in the proper order" just means
    "give it the right episode number". That's why this tool has no
    Move Up / Move Down buttons, unlike Ranked Games Manager.

  - Episode .md files are parsed/rendered through PyYAML. Only the six
    fields this tool exposes (title, episodeNumber, publishDate,
    listenUrl, coverImage, summary) are ever changed; anything else in a
    file is written back untouched. Re-saving an episode with no edits
    reproduces its file byte-for-byte, including whichever line ending
    (LF or CRLF) that file already used.

  - Cover art is converted to a 480x480 WebP named ep-<N>.webp, matching
    every existing cover. Pick any common image type (jpg/png/webp/...).

  - publishDate is the day the episode actually AIRED (YYYY-MM-DD), not
    Audiomack's "Release Date" (which changes whenever a file is
    re-uploaded). It's optional; leave it blank if you don't know it.

Only two third-party packages are needed: PyYAML and Pillow. See
README.md in this folder for how to install them and build a standalone
.exe with PyInstaller. Modeled directly on tools/ranked-games-manager in
the Ranked Games repo (same config/runner/commit patterns).
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk, filedialog, messagebox

import yaml

try:
    from PIL import Image
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

try:
    from PIL import ImageTk
    HAVE_IMAGETK = True
except Exception:
    HAVE_IMAGETK = False


APP_TITLE = "Podcast Manager"
CONFIG_FILENAME = "podcast_manager_config.json"

PODCASTS_DIR = Path("src") / "content" / "podcasts"
IMAGES_DIR = Path("public") / "images" / "podcasts"
COVER_SIZE = 480          # every existing cover is 480x480
COVER_QUALITY = 85
PREVIEW_SIZE = 140

# House order for the fields this tool manages. Anything else found in a
# file is kept, after these, in its original order.
KNOWN_KEYS = ["title", "episodeNumber", "publishDate", "listenUrl",
              "coverImage", "summary"]

IMAGE_TYPES = [("Images", "*.webp *.jpg *.jpeg *.png *.gif *.bmp"),
               ("All files", "*.*")]

_AUTO_TITLE_RE = re.compile(r"^Episode \d+ - ")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_URL_RE = re.compile(r"^https?://\S+$")
_AUTO_COVER_RE = re.compile(r"^ep-\d+\.webp$")


# ---------------------------------------------------------------------------
# episode .md files: frontmatter parse/render via PyYAML, body preserved
# ---------------------------------------------------------------------------

class _DQ(str):
    """Marker type: always double-quote this scalar when dumping."""


class _Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)


def _dq_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", str(data), style='"')


yaml.add_representer(_DQ, _dq_representer, Dumper=_Dumper)

_FRONTMATTER_RE = re.compile(r'^---\n(.*?\n)---\n?(.*)$', re.DOTALL)


def _detect_line_ending(raw_text: str) -> str:
    crlf = raw_text.count("\r\n")
    lf_only = raw_text.count("\n") - crlf
    return "\r\n" if crlf > lf_only else "\n"


def _wrap_for_dump(value):
    if isinstance(value, str):
        return _DQ(value)
    if isinstance(value, list):
        return [_wrap_for_dump(v) for v in value]
    if isinstance(value, dict):
        return {k: _wrap_for_dump(v) for k, v in value.items()}
    return value


def _ordered(data: dict) -> dict:
    out = {k: data[k] for k in KNOWN_KEYS if k in data}
    for k, v in data.items():
        if k not in out:
            out[k] = v
    return out


@dataclass
class EpisodeFile:
    path: Path
    data: dict           # full frontmatter
    body: str = ""       # anything after the closing "---", verbatim
    line_ending: str = "\n"

    @classmethod
    def load(cls, path: Path) -> "EpisodeFile":
        with open(path, "r", encoding="utf-8", newline="") as f:
            raw = f.read()
        line_ending = _detect_line_ending(raw)
        normalized = raw.replace("\r\n", "\n")
        m = _FRONTMATTER_RE.match(normalized)
        if not m:
            raise ValueError(f"{path.name}: no frontmatter block found")
        data = yaml.safe_load(m.group(1)) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path.name}: frontmatter isn't a key/value block")
        return cls(path=path, data=data, body=m.group(2), line_ending=line_ending)

    def render(self) -> str:
        fm_text = yaml.dump(
            _wrap_for_dump(_ordered(self.data)), Dumper=_Dumper,
            default_flow_style=False, allow_unicode=True, sort_keys=False,
            width=100000,
        )
        text = f"---\n{fm_text}---\n{self.body.replace(chr(13) + chr(10), chr(10))}"
        if self.line_ending != "\n":
            text = text.replace("\n", self.line_ending)
        return text

    def save(self):
        with open(self.path, "w", encoding="utf-8", newline="") as f:
            f.write(self.render())

    # convenience accessors -------------------------------------------------
    @property
    def number(self):
        return self.data.get("episodeNumber")

    @property
    def title(self) -> str:
        return str(self.data.get("title", self.path.stem))


# ---------------------------------------------------------------------------
# repo
# ---------------------------------------------------------------------------

class Repo:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.podcasts_dir = self.root / PODCASTS_DIR
        self.images_dir = self.root / IMAGES_DIR
        self.episodes: list[EpisodeFile] = []
        self.problems: list[str] = []
        self.reload()

    @staticmethod
    def looks_like_repo(path: Path) -> bool:
        return (Path(path) / PODCASTS_DIR).is_dir()

    def reload(self):
        self.episodes, self.problems = [], []
        for p in sorted(self.podcasts_dir.glob("*.md")):
            try:
                ep = EpisodeFile.load(p)
            except Exception as e:
                self.problems.append(str(e))
                continue
            if not isinstance(ep.number, int) or isinstance(ep.number, bool):
                self.problems.append(f"{p.name}: episodeNumber is missing or not a whole number")
                continue
            self.episodes.append(ep)
        # Same order the site uses: highest episode number first.
        self.episodes.sort(key=lambda e: e.number, reverse=True)

    def by_number(self, number: int) -> EpisodeFile | None:
        for ep in self.episodes:
            if ep.number == number:
                return ep
        return None

    def next_number(self) -> int:
        return (max((e.number for e in self.episodes), default=-1)) + 1

    def cover_path(self, ep: EpisodeFile) -> Path | None:
        name = ep.data.get("coverImage")
        return (self.images_dir / name) if name else None

    def _free_md_path(self, number: int, current: Path | None = None) -> Path:
        want = self.podcasts_dir / f"episode-{number}.md"
        if current is not None and want == current:
            return want
        if want.exists():
            raise FileExistsError(
                f"{want.name} already exists in src/content/podcasts. "
                "Open that folder and sort it out by hand first.")
        return want

    def save_episode(self, fields: dict, *, editing: EpisodeFile | None,
                     new_cover: Path | None, remove_cover: bool,
                     crop_square: bool = True) -> EpisodeFile:
        """Create or update one episode.

        `fields` holds title / episodeNumber / publishDate / listenUrl /
        summary; an empty-string optional field means "not set" and the
        key is dropped from the file rather than written as "".
        """
        number = fields["episodeNumber"]
        clash = self.by_number(number)
        if clash is not None and clash is not editing:
            raise ValueError(f"Episode {number} already exists: {clash.title}")

        if editing is None:
            ep = EpisodeFile(path=self._free_md_path(number), data={})
        else:
            ep = editing
        old_path, old_number = ep.path, ep.number

        for key in ("title", "episodeNumber", "listenUrl"):
            ep.data[key] = fields[key]
        for key in ("publishDate", "summary"):
            if fields.get(key):
                ep.data[key] = fields[key]
            else:
                ep.data.pop(key, None)

        # -- cover art ------------------------------------------------------
        self.images_dir.mkdir(parents=True, exist_ok=True)
        auto_name = f"ep-{number}.webp"
        current = ep.data.get("coverImage")
        if new_cover is not None:
            install_cover(new_cover, self.images_dir / auto_name, crop_square)
            ep.data["coverImage"] = auto_name
        elif remove_cover:
            ep.data.pop("coverImage", None)   # image file itself stays on disk
        elif (current and editing is not None and old_number != number
              and _AUTO_COVER_RE.match(current)):
            # Renumbered: keep the cover's name in step with the episode,
            # but only when nothing is already sitting at the new name.
            src, dst = self.images_dir / current, self.images_dir / auto_name
            if src.is_file() and not dst.exists():
                src.rename(dst)
                ep.data["coverImage"] = auto_name

        # -- file name follows the episode number ---------------------------
        if editing is not None and old_number != number \
                and old_path.name == f"episode-{old_number}.md":
            ep.path = self._free_md_path(number, current=old_path)
        ep.save()
        if ep.path != old_path and old_path.exists():
            old_path.unlink()
        self.reload()
        return self.by_number(number) or ep

    def remove_episode(self, ep: EpisodeFile, delete_cover: bool):
        cover = self.cover_path(ep)
        if ep.path.exists():
            ep.path.unlink()
        if delete_cover and cover is not None and cover.is_file():
            cover.unlink()
        self.reload()


def install_cover(source: Path, dest: Path, crop_square: bool = True):
    """Write `source` to `dest` as a WebP no larger than 480px a side.

    Square art comes out exactly like the existing covers (480x480).
    Non-square art is centre-cropped to a square when `crop_square` is
    set, otherwise just shrunk to fit with its shape kept.
    """
    if not HAVE_PIL:
        raise RuntimeError(
            "Pillow isn't installed, so cover art can't be converted.\n"
            "Install it with:  pip install pillow")
    with Image.open(source) as im:
        im.seek(0)
        im = im.convert("RGB")
        w, h = im.size
        if crop_square and w != h:
            side = min(w, h)
            left, top = (w - side) // 2, (h - side) // 2
            im = im.crop((left, top, left + side, top + side))
        if max(im.size) > COVER_SIZE:
            im.thumbnail((COVER_SIZE, COVER_SIZE), Image.LANCZOS)
        tmp = dest.with_suffix(".tmp.webp")
        im.save(tmp, "WEBP", quality=COVER_QUALITY, method=6)
    os.replace(tmp, dest)


def is_square(path: Path) -> bool:
    try:
        with Image.open(path) as im:
            return im.size[0] == im.size[1]
    except Exception:
        return True


# ---------------------------------------------------------------------------
# config (remembers the repo folder between runs)
# ---------------------------------------------------------------------------

def _config_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).resolve().parent
    return base / CONFIG_FILENAME


def load_config() -> dict:
    path = _config_path()
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_config(cfg: dict):
    try:
        _config_path().write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# subprocess runner (used for `npm run build` and git) with a live log window
# ---------------------------------------------------------------------------

class RunnerWindow(tk.Toplevel):
    def __init__(self, parent, title: str, cwd: Path, commands: list[list[str]],
                 on_done=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("760x480")
        self._on_done = on_done

        self.text = tk.Text(self, wrap="word", font=("Consolas", 9))
        self.text.pack(fill="both", expand=True, padx=8, pady=8)
        scroll = ttk.Scrollbar(self.text, command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        self.close_btn = ttk.Button(btn_row, text="Close", command=self.destroy,
                                    state="disabled")
        self.close_btn.pack(side="right")

        self._queue: queue.Queue = queue.Queue()
        self._cwd = cwd
        self._commands = commands
        threading.Thread(target=self._run_all, daemon=True).start()
        self.after(80, self._poll)

    def _log(self, line: str):
        self._queue.put(line)

    def _run_all(self):
        ok = True
        # No console window flashing up behind the app on Windows.
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        for cmd in self._commands:
            self._log(f"$ {' '.join(cmd)}\n")
            try:
                # shell=False on purpose: a commit message containing "&"
                # must reach git as one argument (see the Ranked Games
                # Manager bug fixed 2026-09-23).
                proc = subprocess.Popen(
                    cmd, cwd=str(self._cwd), stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, bufsize=1,
                    shell=False, creationflags=flags,
                    encoding="utf-8", errors="replace",
                )
            except FileNotFoundError as e:
                self._log(f"\n!! Could not run this command: {e}\n")
                ok = False
                break
            assert proc.stdout is not None
            for line in proc.stdout:
                self._log(line)
            proc.wait()
            if proc.returncode != 0:
                self._log(f"\n!! Exited with code {proc.returncode}\n")
                ok = False
                break
            self._log("\n")
        self._queue.put(("__DONE__", ok))

    def _poll(self):
        try:
            while True:
                item = self._queue.get_nowait()
                if isinstance(item, tuple) and item[0] == "__DONE__":
                    self.text.insert("end", "Finished OK.\n" if item[1]
                                     else "Stopped: see the error above.\n")
                    self.text.see("end")
                    self.close_btn.configure(state="normal")
                    if self._on_done:
                        self._on_done(item[1])
                    return
                self.text.insert("end", item)
                self.text.see("end")
        except queue.Empty:
            pass
        self.after(80, self._poll)


def npm_command(script: str) -> list[str]:
    # npm on Windows is a .cmd shim, so this one fixed command (never
    # anything a user typed) goes through `cmd /c`.
    if os.name == "nt":
        return ["cmd", "/c", "npm.cmd", "run", script]
    return ["npm", "run", script]


def git_command(*args: str) -> list[str]:
    return ["git", *args]


# ---------------------------------------------------------------------------
# Add / Edit episode dialog
# ---------------------------------------------------------------------------

class EpisodeFormDialog(tk.Toplevel):
    def __init__(self, parent, repo: Repo, *, editing: EpisodeFile | None = None):
        super().__init__(parent)
        self.repo = repo
        self.editing = editing
        self.saved: EpisodeFile | None = None
        self.title("Edit Episode" if editing else "Add New Episode")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._new_cover: Path | None = None
        self._remove_cover = False
        self._preview_img = None

        d = editing.data if editing else {}
        number = editing.number if editing else repo.next_number()

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)
        frm.columnconfigure(1, weight=1)
        row = 0

        ttk.Label(frm, text="Episode number").grid(row=row, column=0, sticky="w", pady=3, padx=(0, 10))
        self.number_var = tk.StringVar(value=str(number))
        num_row = ttk.Frame(frm)
        num_row.grid(row=row, column=1, sticky="w", pady=3)
        ttk.Spinbox(num_row, from_=0, to=9999, width=7,
                    textvariable=self.number_var).pack(side="left")
        ttk.Label(num_row, text="  sets its place in the list (highest number is on top)",
                  foreground="#666").pack(side="left")
        self.number_var.trace_add("write", self._on_number_changed)
        row += 1

        ttk.Label(frm, text="Title").grid(row=row, column=0, sticky="w", pady=3, padx=(0, 10))
        self.title_var = tk.StringVar(
            value=d.get("title", f"Episode {number} - "))
        self.title_entry = ttk.Entry(frm, textvariable=self.title_var, width=62)
        self.title_entry.grid(row=row, column=1, sticky="we", pady=3)
        row += 1

        ttk.Label(frm, text="Air date").grid(row=row, column=0, sticky="w", pady=3, padx=(0, 10))
        date_row = ttk.Frame(frm)
        date_row.grid(row=row, column=1, sticky="w", pady=3)
        self.date_var = tk.StringVar(value=str(d.get("publishDate", "") or ""))
        ttk.Entry(date_row, textvariable=self.date_var, width=14).pack(side="left")
        ttk.Button(date_row, text="Today", width=7,
                   command=lambda: self.date_var.set(_dt.date.today().isoformat())
                   ).pack(side="left", padx=(6, 0))
        ttk.Label(date_row, text="  YYYY-MM-DD, optional. The day it aired.",
                  foreground="#666").pack(side="left")
        row += 1

        ttk.Label(frm, text="Audiomack link").grid(row=row, column=0, sticky="w", pady=3, padx=(0, 10))
        self.url_var = tk.StringVar(value=d.get("listenUrl", ""))
        ttk.Entry(frm, textvariable=self.url_var, width=62).grid(
            row=row, column=1, sticky="we", pady=3)
        row += 1

        ttk.Label(frm, text="Summary").grid(row=row, column=0, sticky="nw", pady=3)
        self.summary_text = tk.Text(frm, width=62, height=3, wrap="word")
        self.summary_text.insert("1.0", d.get("summary", "") or "")
        self.summary_text.grid(row=row, column=1, sticky="we", pady=3)
        row += 1
        ttk.Label(frm, text="Optional. One or two lines shown under the title.",
                  foreground="#666").grid(row=row, column=1, sticky="w")
        row += 1

        ttk.Label(frm, text="Cover art").grid(row=row, column=0, sticky="nw", pady=(10, 3))
        cover = ttk.Frame(frm)
        cover.grid(row=row, column=1, sticky="w", pady=(10, 3))
        self.preview = tk.Label(cover, width=PREVIEW_SIZE, height=PREVIEW_SIZE,
                                relief="groove", bd=1, text="no cover",
                                image=self._blank_image(), compound="center")
        self.preview.pack(side="left")
        side = ttk.Frame(cover)
        side.pack(side="left", padx=(10, 0), anchor="n")
        ttk.Button(side, text="Choose Image...", command=self._browse_cover,
                   width=18).pack(anchor="w", pady=(0, 4))
        ttk.Button(side, text="Remove Cover", command=self._clear_cover,
                   width=18).pack(anchor="w")
        self.cover_var = tk.StringVar()
        ttk.Label(side, textvariable=self.cover_var, foreground="#444",
                  wraplength=300, justify="left").pack(anchor="w", pady=(8, 0))
        row += 1

        btn_row = ttk.Frame(frm)
        btn_row.grid(row=row, column=0, columnspan=2, sticky="e", pady=(14, 0))
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_row, text="Save" if editing else "Add Episode",
                   command=self._on_submit).pack(side="right")

        self._refresh_cover()
        self.bind("<Escape>", lambda e: self.destroy())
        self.title_entry.focus_set()
        self.title_entry.icursor("end")

    # -- helpers ---------------------------------------------------------

    def _blank_image(self):
        # A 1x1 image makes tk.Label's width/height count in pixels.
        self._blank = tk.PhotoImage(width=1, height=1)
        return self._blank

    def _on_number_changed(self, *_):
        """Keep an untouched "Episode N - " title prefix in step."""
        raw = self.number_var.get().strip()
        if not raw.isdigit():
            return
        title = self.title_var.get()
        if _AUTO_TITLE_RE.match(title):
            self.title_var.set(_AUTO_TITLE_RE.sub(f"Episode {int(raw)} - ", title, count=1))

    def _current_cover_file(self) -> Path | None:
        if self._new_cover is not None:
            return self._new_cover
        if self._remove_cover or self.editing is None:
            return None
        p = self.repo.cover_path(self.editing)
        return p if p is not None and p.is_file() else None

    def _refresh_cover(self):
        path = self._current_cover_file()
        if self._new_cover is not None:
            self.cover_var.set(f"New: {self._new_cover.name}\n(saved as a 480px WebP)")
        elif path is not None:
            self.cover_var.set(f"Current: {path.name}")
        elif (self.editing is not None and not self._remove_cover
              and self.editing.data.get("coverImage")):
            self.cover_var.set(f"Missing file: {self.editing.data['coverImage']}")
        else:
            self.cover_var.set("No cover art.")
        self._preview_img = None
        if path is not None and HAVE_PIL and HAVE_IMAGETK:
            try:
                with Image.open(path) as im:
                    im = im.convert("RGB")
                    im.thumbnail((PREVIEW_SIZE, PREVIEW_SIZE))
                    self._preview_img = ImageTk.PhotoImage(im, master=self)
            except Exception:
                self._preview_img = None
        if self._preview_img is not None:
            self.preview.configure(image=self._preview_img, text="")
        else:
            self.preview.configure(image=self._blank,
                                   text="no cover" if path is None else "(no preview)")

    def _browse_cover(self):
        chosen = filedialog.askopenfilename(parent=self, title="Choose cover art",
                                            filetypes=IMAGE_TYPES)
        if not chosen:
            return
        p = Path(chosen)
        try:
            with Image.open(p) as im:
                im.verify()
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"That file couldn't be read as an image:\n{e}",
                                 parent=self)
            return
        self._new_cover, self._remove_cover = p, False
        self._refresh_cover()

    def _clear_cover(self):
        self._new_cover, self._remove_cover = None, True
        self._refresh_cover()

    # -- submit ----------------------------------------------------------

    def _on_submit(self):
        def fail(msg):
            messagebox.showerror(APP_TITLE, msg, parent=self)

        raw_num = self.number_var.get().strip()
        if not raw_num.isdigit():
            return fail("Episode number must be a whole number (0 or higher).")
        number = int(raw_num)
        title = self.title_var.get().strip()
        if not title or _AUTO_TITLE_RE.fullmatch(title + " "):
            return fail("Give the episode a title, e.g. \"Episode 45 - Topic\".")
        date = self.date_var.get().strip()
        if date:
            if not _DATE_RE.match(date):
                return fail("Air date must look like 2023-04-15 (or leave it blank).")
            try:
                _dt.date.fromisoformat(date)
            except ValueError:
                return fail(f"{date} isn't a real calendar date.")
        url = self.url_var.get().strip()
        if not _URL_RE.match(url):
            return fail("Paste the episode's full Audiomack link "
                        "(it should start with https://).")
        clash = self.repo.by_number(number)
        if clash is not None and clash is not self.editing:
            return fail(f"Episode {number} already exists:\n{clash.title}\n\n"
                        "Pick a different number, or edit that episode instead.")

        crop = True
        if self._new_cover is not None and not is_square(self._new_cover):
            answer = messagebox.askyesnocancel(
                APP_TITLE,
                "This image isn't square, and every other cover is.\n\n"
                "Yes = crop it to a centred square (matches the others)\n"
                "No = keep its shape, just shrink it",
                parent=self)
            if answer is None:
                return
            crop = answer

        fields = {
            "title": title,
            "episodeNumber": number,
            "publishDate": date,
            "listenUrl": url,
            "summary": " ".join(self.summary_text.get("1.0", "end").split()),
        }
        try:
            self.saved = self.repo.save_episode(
                fields, editing=self.editing, new_cover=self._new_cover,
                remove_cover=self._remove_cover, crop_square=crop)
        except Exception as e:
            return fail(f"Couldn't save the episode:\n{e}")
        self.destroy()


# ---------------------------------------------------------------------------
# small dialogs
# ---------------------------------------------------------------------------

class RemoveConfirmDialog(tk.Toplevel):
    def __init__(self, parent, title_text: str, has_cover: bool):
        super().__init__(parent)
        self.title("Remove Episode")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = False
        self.delete_cover = False

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text=f"Remove this episode from the site?\n\n{title_text}",
                  wraplength=420, justify="left").pack(anchor="w")
        ttk.Label(frm, text="Its episode file is deleted. Until you commit, "
                  "git can still bring it back.",
                  foreground="#666", wraplength=420, justify="left").pack(anchor="w", pady=(8, 0))
        self.cover_var = tk.BooleanVar(value=False)
        if has_cover:
            ttk.Checkbutton(frm, text="Also delete its cover image",
                            variable=self.cover_var).pack(anchor="w", pady=(10, 0))
        btn_row = ttk.Frame(frm)
        btn_row.pack(fill="x", pady=(14, 0))
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_row, text="Remove", command=self._confirm).pack(side="right")

    def _confirm(self):
        self.result = True
        self.delete_cover = self.cover_var.get()
        self.destroy()


class CommitDialog(tk.Toplevel):
    def __init__(self, parent, default_message: str):
        super().__init__(parent)
        self.title("Commit & Push")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = False

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill="both", expand=True)
        ttk.Label(frm, text="Commit message:").pack(anchor="w")
        self.text = tk.Text(frm, width=60, height=4, wrap="word")
        self.text.insert("1.0", default_message)
        self.text.pack(pady=(4, 8))
        ttk.Label(frm, text="Only podcast episode files and podcast cover images "
                  "are included in the commit.", foreground="#666",
                  wraplength=440, justify="left").pack(anchor="w")
        self.push_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frm, text="Push to remote after committing (this deploys the site)",
                        variable=self.push_var).pack(anchor="w", pady=(6, 0))

        btn_row = ttk.Frame(frm)
        btn_row.pack(fill="x", pady=(12, 0))
        ttk.Button(btn_row, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(btn_row, text="Commit", command=self._confirm).pack(side="right")

    def _confirm(self):
        self.message = self.text.get("1.0", "end").strip()
        self.push = self.push_var.get()
        if not self.message:
            messagebox.showerror(APP_TITLE, "Commit message can't be empty.", parent=self)
            return
        self.result = True
        self.destroy()


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("860x620")
        self.minsize(680, 420)

        self.repo: Repo | None = None
        self._last_change = ""
        self._build_widgets()

        repo_path = load_config().get("repo_path")
        if repo_path and Repo.looks_like_repo(Path(repo_path)):
            self._open_repo(Path(repo_path))
        else:
            self.after(200, self._prompt_for_repo)

    # -- layout --------------------------------------------------------

    def _build_widgets(self):
        top = ttk.Frame(self, padding=(8, 8, 8, 0))
        top.pack(fill="x")
        ttk.Label(top, text="Repo folder:").pack(side="left")
        self.repo_label_var = tk.StringVar(value="(none selected)")
        # Buttons are packed first (on the right) so a long folder path
        # can never push them off the edge of the window.
        ttk.Button(top, text="Reload", command=self._reload).pack(side="right", padx=(6, 0))
        ttk.Button(top, text="Change Folder...", command=self._prompt_for_repo).pack(side="right")
        ttk.Label(top, textvariable=self.repo_label_var, foreground="#444").pack(
            side="left", padx=(4, 12))

        search_row = ttk.Frame(self, padding=(8, 8, 8, 0))
        search_row.pack(fill="x")
        ttk.Label(search_row, text="Filter:").pack(side="left")
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._refresh_list())
        ttk.Entry(search_row, textvariable=self.filter_var, width=40).pack(
            side="left", padx=(4, 0))
        ttk.Label(search_row, text="   Listed in site order: newest episode number first.",
                  foreground="#666").pack(side="left")

        body = ttk.Frame(self, padding=8)
        body.pack(fill="both", expand=True)

        list_frame = ttk.Frame(body)
        list_frame.pack(side="left", fill="both", expand=True)
        columns = ("num", "title", "date", "cover")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings",
                                 selectmode="browse")
        self.tree.heading("num", text="Ep")
        self.tree.heading("title", text="Title")
        self.tree.heading("date", text="Air date")
        self.tree.heading("cover", text="Cover")
        self.tree.column("num", width=44, anchor="center", stretch=False)
        self.tree.column("title", width=400, anchor="w")
        self.tree.column("date", width=90, anchor="center", stretch=False)
        self.tree.column("cover", width=70, anchor="center", stretch=False)
        self.tree.pack(side="left", fill="both", expand=True)
        vs = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vs.set)
        vs.pack(side="left", fill="y")
        self.tree.bind("<Double-1>", lambda e: self._edit_selected())
        self.tree.tag_configure("warn", foreground="#b05a00")

        side = ttk.Frame(body)
        side.pack(side="left", fill="y", padx=(10, 0))
        ttk.Button(side, text="Add New Episode...", command=self._add_episode, width=20).pack(pady=2)
        ttk.Button(side, text="Edit Selected...", command=self._edit_selected, width=20).pack(pady=2)
        ttk.Button(side, text="Remove Selected...", command=self._remove_selected, width=20).pack(pady=2)
        ttk.Separator(side, orient="horizontal").pack(fill="x", pady=8)
        ttk.Button(side, text="Open Link in Browser", command=self._open_link, width=20).pack(pady=2)
        ttk.Button(side, text="Open Image Folder", command=self._open_image_folder, width=20).pack(pady=2)
        ttk.Separator(side, orient="horizontal").pack(fill="x", pady=8)
        ttk.Button(side, text="Validate Build", command=self._validate_build, width=20).pack(pady=2)
        ttk.Button(side, text="Commit && Push...", command=self._commit_push, width=20).pack(pady=2)

        bottom = ttk.Frame(self, padding=(8, 0, 8, 8))
        bottom.pack(fill="x")
        self.status_var = tk.StringVar(value="")
        ttk.Label(bottom, textvariable=self.status_var, foreground="#2a7a2a").pack(side="left")

    # -- repo management -------------------------------------------------

    def _prompt_for_repo(self):
        path = filedialog.askdirectory(title="Select your Backlog_Website_Home folder")
        if not path:
            if self.repo is None:
                self.status_var.set("No repo folder selected yet.")
            return
        p = Path(path)
        if not Repo.looks_like_repo(p):
            messagebox.showerror(
                APP_TITLE,
                f"{p}\n\ndoesn't look right. Expected to find "
                "src/content/podcasts under it. Pick the folder that directly "
                "contains 'src' and 'public' (normally Backlog_Website_Home).",
            )
            return
        self._open_repo(p)

    def _open_repo(self, path: Path):
        try:
            self.repo = Repo(path)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Couldn't open that repo:\n{e}")
            return
        self.repo_label_var.set(str(path))
        save_config({"repo_path": str(path)})
        self._refresh_list()
        self.status_var.set(f"Loaded {len(self.repo.episodes)} episodes.")
        self._report_problems()

    def _reload(self):
        if not self.repo:
            return
        self.repo.reload()
        self._refresh_list()
        self.status_var.set("Reloaded from disk.")
        self._report_problems()

    def _report_problems(self):
        if self.repo and self.repo.problems:
            messagebox.showwarning(
                APP_TITLE,
                "These episode files couldn't be read and are not listed:\n\n"
                + "\n".join(self.repo.problems))

    def _require_repo(self) -> bool:
        if self.repo is None:
            messagebox.showwarning(APP_TITLE, "Select your repo folder first.")
            return False
        return True

    # -- list rendering ----------------------------------------------------

    def _refresh_list(self, select_number: int | None = None):
        self.tree.delete(*self.tree.get_children())
        if not self.repo:
            return
        needle = self.filter_var.get().strip().lower()
        for ep in self.repo.episodes:
            if needle and needle not in ep.title.lower() and needle != str(ep.number):
                continue
            cover = self.repo.cover_path(ep)
            if cover is None:
                cover_text, tags = "none", ("warn",)
            elif not cover.is_file():
                cover_text, tags = "missing", ("warn",)
            else:
                cover_text, tags = "yes", ()
            self.tree.insert("", "end", iid=str(ep.number), tags=tags, values=(
                ep.number, ep.title, ep.data.get("publishDate", "") or "", cover_text))
        if select_number is not None and self.tree.exists(str(select_number)):
            self.tree.selection_set(str(select_number))
            self.tree.see(str(select_number))

    def _selected(self) -> EpisodeFile | None:
        sel = self.tree.selection()
        if not sel or not self.repo:
            return None
        return self.repo.by_number(int(sel[0]))

    def _need_selection(self) -> EpisodeFile | None:
        if not self._require_repo():
            return None
        ep = self._selected()
        if ep is None:
            messagebox.showinfo(APP_TITLE, "Select an episode in the list first.")
        return ep

    # -- actions -------------------------------------------------------------

    def _add_episode(self):
        if not self._require_repo():
            return
        dlg = EpisodeFormDialog(self, self.repo)
        self.wait_window(dlg)
        if dlg.saved is not None:
            self._last_change = f"Add {dlg.saved.title}"
            self._refresh_list(dlg.saved.number)
            self.status_var.set(f"Added: {dlg.saved.title}")

    def _edit_selected(self):
        ep = self._need_selection()
        if ep is None:
            return
        dlg = EpisodeFormDialog(self, self.repo, editing=ep)
        self.wait_window(dlg)
        if dlg.saved is not None:
            self._last_change = f"Update {dlg.saved.title}"
            self._refresh_list(dlg.saved.number)
            self.status_var.set(f"Saved: {dlg.saved.title}")

    def _remove_selected(self):
        ep = self._need_selection()
        if ep is None:
            return
        cover = self.repo.cover_path(ep)
        dlg = RemoveConfirmDialog(self, ep.title, bool(cover and cover.is_file()))
        self.wait_window(dlg)
        if not dlg.result:
            return
        title = ep.title
        try:
            self.repo.remove_episode(ep, dlg.delete_cover)
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Couldn't remove it:\n{e}")
            return
        self._last_change = f"Remove {title}"
        self._refresh_list()
        self.status_var.set(f"Removed: {title}")

    def _open_link(self):
        ep = self._need_selection()
        if ep is None:
            return
        url = str(ep.data.get("listenUrl", ""))
        if _URL_RE.match(url):
            import webbrowser
            webbrowser.open(url)

    def _open_image_folder(self):
        if not self._require_repo():
            return
        folder = self.repo.images_dir
        folder.mkdir(parents=True, exist_ok=True)
        try:
            if os.name == "nt":
                os.startfile(str(folder))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(folder)])
            else:
                subprocess.Popen(["xdg-open", str(folder)])
        except Exception as e:
            messagebox.showerror(APP_TITLE, f"Couldn't open the folder:\n{e}")

    # -- build / git -----------------------------------------------------

    def _validate_build(self):
        if not self._require_repo():
            return
        RunnerWindow(self, "Validating build (npm run build)", self.repo.root,
                     [npm_command("build")])

    def _commit_push(self):
        if not self._require_repo():
            return
        dlg = CommitDialog(self, self._last_change or "Update podcast list")
        self.wait_window(dlg)
        if not dlg.result:
            return
        # Scoped on purpose: only podcast content + podcast covers, never
        # `git add -A`, so nothing else sitting in the repo gets swept in.
        commands = [
            git_command("add", "-A", "--", PODCASTS_DIR.as_posix(), IMAGES_DIR.as_posix()),
            git_command("commit", "-m", dlg.message),
        ]
        if dlg.push:
            commands.append(git_command("push"))
        RunnerWindow(self, "Commit & Push", self.repo.root, commands)


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
