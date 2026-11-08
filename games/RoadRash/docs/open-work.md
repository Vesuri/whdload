# Open work

## Where it stands

3.0b (22.10.2026) is complete under the agreed emulator scope: plan items A–C and G
complete, D, E and F1–F5 complete, H1/H2 investigated (`performance-plan.md`). The release
slave is built from the tree submitted and merged upstream, the last commit of this history
("Road Rash 3.0b: optional enhanced framerate"); `release/slaves.sha256` pins it.

That tree is the development branch reduced to its release configuration (no VERIFY
instrumentation, development notes or packager), so its slave differs from the development
tip's (`55f24917…`, the build `release.md` and `framerate-comparison.md` describe, and the one
the A1200-030 playtest used). Before it was submitted, the cleaned slave (`e3f92ce3…`) ran
`framerate-comparison.md`'s benchmark on its five machines, CUSTOM2 off and on, once each,
and gave every rate in its table (`tools/merge_clean_check.py`). A 040 replay of both slaves
with CUSTOM2=1 agreed in the start state, the crash onsets and 76 of 77 sampled race states;
in the other (sample 60 of the 20-field samples) the moving riders' positions differ by about
10,000 units, and every later sample agrees again.

## Upstream after the merge

JOTD merged the branch in e72e067b (24.10.2026) and has not released it. His 8c35810f
("merged a few slaves", 31.10.2026) then changed `R/RoadRash/usr`:

- `ReadJoypad.s` reads the controllers with `resload_ReadJoyPort` instead of the CIA/POTGO
  code, and the ReadMe's requirement becomes WHDLoad 19.
- The version string is "3.0" plus the build date (`DATETIME` or Barfly's `WDate`), not
  "3.0b (22.10.2026)"; the ReadMe's entry becomes "Version 3.0 (22.10.2026) done by
  Versuri/JOTD" (sic) with "adapted to whdload ReadJoyPad routine".
- In `pl_main`, `PL_IFC2` moves above the rider-visibility (`PL_P $9E2C`) and border-blank
  (`PL_PS $2874E`) patches, so those two fixes apply only with CUSTOM2 on. Our ReadMe says
  the visual fixes apply in both modes.

None of it is in `src/` here; the release ships the merged tree as built. Taking the
ReadJoyPort change means WHDLoad 19 and a controller retest (joystick, CD32 pad, name and
password entry); the `PL_IFC2` move is a behaviour change to decide on, not a fix.

## Open

- Unreleased: blitter waits after the unwaited blits in the intro, title, loader,
  menus and bike shop, in both modes (`visual-fixes.md`, "Unwaited blits"). They
  address the player report of intro and bike-shop glitches (8.11.2026, 68040).
  The emulator doesn't reproduce the glitches, so the fix needs a player's
  confirmation on hardware. The release slave and `release/slaves.sha256` are
  still 3.0b's. A release needs a version, a ReadMe history entry and the release
  checks.
- Race-start blits the observer still reports (CUSTOM2=0, `a1200-fast`): the CPU
  reads and writes the D area of the blit at main hunk `$346e0` (from `$33a3e`),
  and reprograms the blitter while the blits at `$32e14` (from `$32e2a`) and
  `$32f8a` (from `$32f96`..`$32fc0`) run. The observer logs each site once, so
  they may happen every frame. No glitch has been reported there. A wait in the
  race path costs time, so any fix needs the rate checks.
- D1d: real 68040/68060 cache and coherency testing (emulator only so far).
- F6a–F6d: relocating the fixed-address CPU globals, future work by agreement.
- Testing on real hardware in general; the release's limitations are in `release.md`.
