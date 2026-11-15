Original Xbox shelf covers
==========================

Each game's cover is a file named <id>.jpg (or .png / .webp) in this folder.
The page uses it automatically at build time; a game with no file shows a title card.
To add or replace a cover: drop a correctly-named image here, then git add / commit / push.
Ids come from src/lib/andyOriginalXbox.ts.

Currently showing a title card (no matching Xbox-era cover found yet):

  counter-strike.jpg   (Counter-Strike)
  fable-the-lost-chapters.jpg   (Fable: The Lost Chapters)
  far-cry-instincts-evolution.jpg   (Far Cry Instincts Evolution)
  future-tactics-the-uprising.jpg   (Future Tactics: The Uprising)
  godzilla-save-the-earth.jpg   (Godzilla: Save the Earth)
  guilty-gear-x2.jpg   (Guilty Gear X2)
  heroes-of-the-pacific.jpg   (Heroes of the Pacific)
  mercenaries-playground-of-destruction.jpg   (Mercenaries: Playground of Destruction)
  midway-arcade-treasures-2.jpg   (Midway Arcade Treasures 2)
  ninja-gaiden-black.jpg   (Ninja Gaiden Black)
  phantasy-star-online-episode-i-and-ii.jpg   (Phantasy Star Online Episode I & II)
  return-to-castle-wolfenstein-tides-of-war.jpg   (Return to Castle Wolfenstein: Tides of War)
  robotech-battlecry.jpg   (Robotech: Battlecry)
  rogue-ops.jpg   (Rogue Ops)
  shattered-union.jpg   (Shattered Union)
  shenmue-ii.jpg   (Shenmue II)
  sid-meiers-pirates.jpg   (Sid Meier's Pirates!)
  soulcalibur-ii.jpg   (Soulcalibur II)
  splinter-cell.jpg   (Splinter Cell)
  splinter-cell-chaos-theory.jpg   (Splinter Cell: Chaos Theory)
  splinter-cell-pandora-tomorrow.jpg   (Splinter Cell: Pandora Tomorrow)
  star-wars-battlefront-ii.jpg   (Star Wars: Battlefront II)
  taito-legends.jpg   (Taito Legends)
  timesplitters-2.jpg   (TimeSplitters 2)
  timesplitters-future-perfect.jpg   (TimeSplitters: Future Perfect)
  tron-2-0-killer-app.jpg   (Tron 2.0: Killer App)

Bigger pictures (optional)
--------------------------
Clicking a cover opens that game's own page. It shows the normal cover by default. For a
sharper image there, add a second file named <id>-large.jpg (or .png / .webp) in this folder,
e.g. halo-2-large.jpg. No other change is needed; the game page picks it up at build time.

Extra pictures for a game (optional, your own screenshots/photos)
-----------------------------------------------------------------
Make a folder in this directory named exactly like the game's id and put images in it:

  original-xbox/halo-2/shot1.jpg
  original-xbox/halo-2/shot2.jpg

They show up as a "More pictures" gallery on that game's page, in filename order
(1, 2, 10 sort correctly). Click a picture to open it full size. Games with no folder
simply have no gallery. Allowed types: jpg, jpeg, png, webp, gif, svg.
