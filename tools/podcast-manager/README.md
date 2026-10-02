# Podcast Manager

A small Windows desktop tool for maintaining the podcast list at
deathbybacklog.com/podcasts/ without needing Claude (or any AI) for
routine edits:

- Add a new episode: number, title, air date, Audiomack link, cover art
- Edit an existing episode, including its number and its cover art
- Remove an episode
- Validate the site still builds (`npm run build`)
- Commit & push the change to git (the push is what deploys the site)

It edits the exact same files a human (or Claude) would edit by hand:
`src/content/podcasts/episode-<N>.md` and
`public/images/podcasts/ep-<N>.webp`. Re-saving an episode with no edits
reproduces its file byte-for-byte, so it's safe to open and poke around.

It's the sibling of Ranked Games Manager
(`Claude_BacklogWebsite/tools/ranked-games-manager`) and works the same
way: same setup, same folder picker, same Validate / Commit buttons.

## How ordering works

The Podcasts page, and the "Latest Podcast" tile on Home, sort by
**episode number, highest first**. There is no separate order file. So
putting an episode "in the proper order" means giving it the right
episode number, and that's why there are no Move Up / Move Down buttons
here. The list in the app is shown in the same order the site uses.

## One-time setup (do this once)

You need Python installed on Windows once, just to build the .exe. If
you already built Ranked Games Manager on this PC, you have it.

1. Open PowerShell in this folder (`tools/podcast-manager/` in the
   `Backlog_Website_Home` repo) and run:

   ```powershell
   pip install -r requirements.txt
   pyinstaller --onefile --windowed --name "PodcastManager" podcast_manager.py
   ```

2. That creates `dist\PodcastManager.exe`. Move it wherever you like; it
   is standalone from this point on.

3. Double-click it. The first time, it asks for your repo folder: pick
   the one that directly contains `src` and `public`, normally
   `D:\OneDrive\Podcasts\Website\Backlog_Website_Home`. It remembers
   that in a small config file next to the .exe.

To update the tool later, repeat step 1 with the new `podcast_manager.py`.

## Adding a new episode

1. Upload the episode to Audiomack and copy its link.
2. Click **Add New Episode...**. The number is pre-filled with the next
   one, and the title starts as `Episode <N> - ` for you to finish.
3. Fill in:
   - **Air date**: `YYYY-MM-DD`, the day it actually aired. Optional.
     Don't use Audiomack's "Release Date"; that changes whenever a file
     is re-uploaded.
   - **Audiomack link**: the full `https://audiomack.com/...` link.
   - **Summary**: optional, one or two lines shown under the title.
   - **Cover art**: click **Choose Image...** and pick any jpg, png or
     webp. It's saved as a 480x480 WebP named `ep-<N>.webp`, matching
     the other covers. If the image isn't square, you're asked whether
     to crop it to a centred square or keep its shape.
4. Click **Add Episode**, then **Validate Build**, then
   **Commit && Push...**.

## The other buttons

- **Edit Selected...** (or double-click a row): same form, pre-filled.
  Changing the episode number moves the episode in the list and renames
  its file and its cover to match.
- **Remove Selected...**: deletes the episode's file, with a checkbox to
  delete its cover image too. Until you commit, git can bring it back.
- **Open Link in Browser**: opens the selected episode on Audiomack, to
  check the link works.
- **Open Image Folder**: opens `public/images/podcasts/` in File Explorer.
- **Validate Build**: runs `npm run build` and shows the output.
- **Commit && Push...**: commits **only** podcast episode files and
  podcast cover images (never anything else sitting in the repo), then
  pushes if the box is ticked. Assumes `git` already works in your VS
  Code terminal.

The **Cover** column shows `yes`, `none` (no cover assigned) or `missing`
(a cover is assigned but the image file isn't there).

## What it won't touch

Any field in an episode file that this tool doesn't show is written back
exactly as it was. Two episodes can't share a number; the tool refuses
and tells you which episode already has it.
