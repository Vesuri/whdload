# Open work — Legends of Valour

Status 2026-10-05: playbook §1–§8 done (fixed window, frame counter, A500-eq. and 68020
baselines; `docs/profiling.md` §6–§7). Next is §9, game time.

## Done

- Repo, rules, harness copied from Test Drive II (`lov.py`, `barto.py`, `lov_report.py`).
- Slave decoded without source (`tools/slave_info.py`) and rebuilt from the disassembly on WHDLoad
  20.0's kick13 example (`whdload/`), with a VERIFY-only input tape (`whdload/tape.s`).
- `AMIGA2` decrunched offline (`tools/unpack.py`); `lov_report.py` names all 17 hunks, the
  Kickstart and the live slave.
- Benchmark route `tools/tapes/spin.txt` (default character, large view, turning right), driven
  by game-state waits; reproducible fixed window `tools/fixed_window.sh` (two boots identical).
- Frame counter: `frames.py` counts the view's chunky-to-planar display step `h12:05ea6`.
- Baseline: **2.5 fps** on the A500-eq., **12.5 fps** on a 14 MHz 68020; render ~45–53%,
  chunky-to-planar ~26–30%, game logic 6–16% (`docs/profiling.md` §7).

## Open questions

- **Game time (§9).** Time sources are the VBL field counter `h11:0602c` and VPOSR reads in
  h12 (`063ac`..`063f0`). Does the world (turning, the townsman) advance per field or per
  rendered frame? The two machines' windows show different scenes at the anchor, and the
  townsman reaches the player much sooner on the 68020: likely per frame. Needs the state map
  (heading `h5:01e64`'s 0–359 value, positions) and a coupling test.
- W0 complete: original/rebuilt start-screen view bytes agree; only pointer coloration and
  three fields of startup timing differ. Hunk table, CPU/CUSTOM2 tags, disabled-hook checker
  and validated breakpoint frame counter are in place (`docs/profiling.md` §8).
- `swap_fields.py` now agrees exactly with the full trace on the A500 fixed window.
- The conversation panel polls through h2, so `W` cannot wait for it; the route clicks EXIT
  blindly. A hook on its poll would make the route shorter.
- Entropy: the windows are identical across boots, so VPOSR reads do not leak into this
  route; re-check for any new route.

## Candidate optimisations (not started; plan in `docs/performance-plan.md`)

- Chunky-to-planar `h12:054ce`: a quarter of the A500 frame. A faster conversion (or blitter
  assisted on the A500, longword merges on 020+) is the classic win.
- Wall column drawer `h12:04c1a` and its setup `h12:02808`: ~38% of the A500 frame.
- Scaled sprites `h12:05114`: up to 13% when people are in view.
