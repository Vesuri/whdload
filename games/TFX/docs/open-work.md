# Open work

## Upstream status

The 2.2 work went upstream as one commit (`tfx-merge`, 0cf43ac9 on the Vesuri fork, the
last commit of this history before the move) and JOTD merged it (pull request #34, merge
1635ba0e). He then fixed his build of it (e0a36226: his Makefile, and the BARFLY/DATETIME
date in `DECL_VERSION` instead of the fixed `2.2 (22.10.2026)`) and in 640b9e0c set the
slave's version to 2.3 and removed a contributor from the slave's credit line (`slv_info`)
at his request. This repository applies that credit change too (the commit after the
move); the version and date stay 2.2 (22.10.2026). Upstream's ReadMe still ends at the
2.2 entry, and whdload.de still offers 2.1 (09.08.2023): upstream has not released it.

Open: release 2.2 here (`make dist` gives TFXEnhanced-2.2-20261022.lha) or wait for
upstream's release.

## Goal (from the user)

Fastest possible 68040 version of TFX (A1200 + Apollo 1240/40 MHz) with native 040 FPU
maths, plus the development-leftover palette glitches. Do not regress 020/030/060.
Plan: `docs/PERFORMANCE_PLAN.md` (original steps 1-14, then the 20 fps action
plan with a status table). Executable survey: `executables.md`; inputs: `development.md`.

## Current state (2026-10-22)

- User-selected integer projection is now the shared optimized tfx.020 default.
  CUSTOM1 and the unused FPU projection helper have been removed in a separate
  reversible change after the 2.2 release metadata update. Revert that change for
  FPU-default comparisons; do not use CUSTOM1. Original rendering and CUSTOM5
  bypasses remain unchanged.

- Executable comparison complete and pushed: renderer support 3802cfd5,
  automatic selector and final plan c4e56b93. `tmp/build/release/TFX.Slave` ==
  `tmp/exe-compare/auto.slave` (auto.lst); no experimental source remains.
- Automatic mode now chooses tfx.020 on FPU-equipped 020/030/040/060; no-FPU CPUs
  keep plain TFX. Original rendering and explicit choices pass. Rotation caching
  stays full-040-only; no delta copy on 020; 060 uses the Gouraud division body.
- Per-CPU action/follow publications over 2,000 fields (TFX -> tfx.020):
  020+68881/882 128->165 / 93->108; 030+882 899->1000 / 567->641;
  060 502->625 / 327->380. Compare only within one emulator CPU model.
- Final checks pass: 68 flight boots, 20 startup cases, 275 native projection cases
  and 2,496 Gouraud rows per newly enabled CPU. FPSPs unchanged. See
  `executable-comparison.md` and `tmp/exe-compare/validation.json`.
- The following 040 figures are the prior reference; this task did not re-profile
  the 040 or establish hardware speed.
- 040 tfx.020 follow camera (F5): 411/2,000, est-040 2.78 M. Plain TFX (020/030/060) now has
  the Gouraud run fill, delta copy (030/060) and mask_sprite8; see the plan's CPU gating review.
- Emulator, action flight: 746/2,000 publications (18.7 nominal fps), estimated 040
  1.69 M cycles per frame (the 2.0 M target is met; 800/2,000 is not).
- Original plan: steps 1-11 and 13 done. Step 12 (palette) unreproduced, see
  `palette-investigation.md`. Step 14: ReadMe and pull request done (merged upstream);
  the hardware test is open.
- 20 fps action plan: steps 0, 2, 4, 6, 7, 8, 9, 11 (Gouraud runs) done; 3 and 5 rejected (3c/3d assessed
  and not worth it); step 1 now uses integer projection by user request.

## Scratch cleanup (2026-10-29)

The evidence below is in the fork worktree's ignored `tmp/dev/tmp/`, not in this game's
`tmp/` until it is copied there (`development.md`). Deleted to free disk (26 GB -> 2 GB): every `*.trace`, run memory dumps (`fast.bin`,
`chip.bin`), raw `profile.csv`, `.run` copies, superseded listings (kept
`tmp/exe-compare/auto.lst`, `tmp/build/`) and old step emulators (rebuild with
`tools/build_*_emulator*`; `tmp/opt20-project-emulator` kept). Evidence directories
keep their reports, JSON, logs and PNGs; rerun a tool to regenerate raw data.

## Open items

The requested FPU-equipped executable comparison is complete. Its tools remain in
`tools/exe_compare_*.py`, `tools/exe_compare_*.sh` and `tools/cpu_profile.py`.
No-FPU or explicit plain-TFX use still has the integer normal_fill/soft-float path;
FPU-equipped automatic mode no longer pays that soft-float cost. Further plain-TFX
ports need a new profile and are not part of the completed comparison.


All remaining performance work needs the Amiga:
1. Run calib040 on the Apollo; replace the constants in `tools/prof20_cost040.py`.
2. Compare integer projection against the reverted FPU-default build on hardware.
3. Hardware in-game FPS (CUSTOM4 bit 3) on both fixtures and the frame-interval
   distribution (20 fps step 10); report it as measured, not as the emulator figure.
4. Step 14: user test on the A1200/040 (the ReadMe and pull request are done).
5. Step 12 palette: needs a reproducible trigger, faulty build or hardware capture.
6. Revisit 3c only if hardware shows the copy loop is bandwidth-bound.

## Harness quick reference

- Strict profiler emulator: `tmp/opt20-project-emulator/fs-uae/fs-uae`; one emulator at a
  time on DEBUG_PORT=2611 (other projects' emulators use other ports). Stop only our PID.
- Build: `make slave`, `make build BUILD=chiponly`, or `tools/build.sh` (OUTPUT_SLAVE=...,
  extra args to vasm, e.g. `-L x.lst`; CHIP_ONLY=1).
- Per-step suites (twins, gates, scenes, balanced pair): `tools/{fade,rot,sfd,poly,sqrt,gouraud}_suite.sh`,
  `step6_suite.sh`, `skip_suite.sh`. Twin tests: `tools/opt20_*_test.py`.
- Profiles: `tools/prof20_analyze.py`, `prof20_cost040.py` (estimated 040),
  `prof20_annotate.py`, A/B with `prof20_ab.py CONTROL LST CANDIDATE LST OUT.json`.
- Balanced pairs: CLOCK_NORMALIZE=1, PATCH_KIND=<kind> in `opt20_balanced_profile.py`;
  scenes switch patches off with <KIND>_OFF in `opt20_scene.py`; gates in `opt20_gate.py`.
- Gouraud scan-table probe: `tools/gouraud_probe.py`; scenes FOLLOW_TAPE=1, GOURAUD_OFF=1.
- Cockpit probe: `tools/cockpit_probe.py` (PROBE, PROBE_FRAMES, NOFILL, VIEW_TAPE,
  PROBE_SIZES).

## Pitfalls

- TFXHD.s uses CRLF line endings: edit as bytes, never write it in Python text mode.
- Step-13 hunk discovery must include lower auxiliary hunks: upper 8 MB, not just
  $41a00000 upward. 020 TFX.FPU/TFX.040 enrolment uses the slow-original-renderer
  waits (3,000 boot fields, 40-field keys, 80-field transitions). Retain rejected
  captures; do not mistake boot-input/discovery failures for game faults.
- Original rendering without FPS has no slave swap hook: use the unconditional
  joystick hook to locate the slave for gate checks.
- The seed's dh0.hdf bakes the WHDLoad CUSTOM arguments: never A/B a CUSTOM option on a
  shared TEST_SEED; select variants with a same-length patch write.
- Frame A/Bs of small changes are swamped by replay divergence (different frames drawn,
  e.g. +4% fill calls): judge small exact changes by routine-level cost and cycle counts.
- The emulator's 040 model is roughly an instruction counter; always check the estimated
  040 cost too.
- Monitor `tfxmem` writes over about 90 bytes time out: chunk them. The debugger stub
  takes about 20 software breakpoints.
- The harness hunk image is unrelocated: rebuild control bytes holding absolutes from the
  live base.
- Poison builds: junk only bytes the original writes, and only after kept registers are
  restored (sibling fills read stale table bytes).
- Game dispatch entries change at run time: twin fixtures must own their chain opcodes.
- Patch lists use 16-bit offsets: big slave tables go at the end of TFXHD.s.
- vasm shortens `0(An)` to `(An)`: never precompute instruction sizes by hand; check them.
- Polygon edge tables hold 17 records per chain (n <= 17 vertices safe).

Older handoffs and the full progress log: `open-work-history.md`.

## Disk cleanup (2026-10-22)

Removed generated test dh0.hdf/dh1.hdf images and locate-fast.bin/locate-chip.bin
hunk-discovery dumps. Inputs, tools, builds, results, screenshots, traces and
other memory captures are retained. The file list (cleanup-2026-10-22.json) stayed in the
fork harness's `docs/`.
Replays must regenerate fresh boot disks; do not assume old seed directories
contain usable images. Checks requiring the deleted discovery dumps need a rerun.
