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

- Unreleased: the intro screen-clear blitter wait now applies in both modes
  (`visual-fixes.md`). The release slave and `release/slaves.sha256` are still
  3.0b's; a release needs a version, ReadMe history entry and the release checks.
- Bike selection screen glitches (player report, 8.11.2026, 68040; not reproduced
  in the emulator). Suspected unwaited blit, as in the intro. Static audit so far:
  the full-screen clear at main-hunk `$2f654`/`$2f67c` returns while clearing but
  serves startup, password and disk-error screens; the clear at `$2ef9e` has no
  direct caller; the end-of-race picture screens (`$3e5a`, `$3eea`) load, copy and
  decode with no blit in flight. The shop's texts (`$3540`..`$3802`) are reached
  through the menu tables at `$2448`..`$2494`. Next: a DMA trace of the shop on
  `a1200-fast` (030+ traces carry no blitter records), reached by finishing a race.
- D1d: real 68040/68060 cache and coherency testing (emulator only so far).
- F6a–F6d: relocating the fixed-address CPU globals, future work by agreement.
- Testing on real hardware in general; the release's limitations are in `release.md`.
