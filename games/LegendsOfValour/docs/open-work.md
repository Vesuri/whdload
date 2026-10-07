# Open work — Legends of Valour

Status 2026-10-07: playbook §1–§8 done (fixed window, frame counter, A500-eq. and 68020
baselines; `docs/profiling.md` §6–§7). W0–W4 complete; measurements in §8. W2 uses
MEMF_PUBLIC on every CPU. Next is W5, ray setup. Frame-rate-independent
simulation timing is required follow-up work (`docs/performance-plan.md` §2.3.1).

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

- W0: shared hunk table, CPU/CUSTOM2 tags, disabled-hook checker and original/rebuilt
  first-button-poll comparison completed; startup pointer/timing limitations in §8.
- W1: CPU-selected Kalms C2P, all three sizes, 1,860 pixel twins passed. Spin fps
  2.5 → 3.0 / 12.4 → 14.8 (A500 / 020); matching-scene wall A/B confirms savings.
  Shipped build excludes VERIFY instruments.
- W2: PUBLIC chunky allocation on every CPU, matching owned free and original-pool fallback;
  2,096 pixel twins across all views plus lifecycle/failure checks passed. Ten fixed-window
  captures: 020 spin 14.9 → 16.0 fps, wall 14.2 → 15.1; stock 68000 FPS unchanged.
  W1+W2 enabled in ignored local preferences (mask 3); audit in `docs/w2-audit.md`.
- `swap_fields.py` agrees exactly with the full trace on the A500 fixed window.

- W3: 68000/10 wall-column unroll verified across all three bodies. Fixed-wall
  column cost −6.6%, renderer −4.6%, fps 3.1 → 3.2; 020 keeps original code
  with identical off/on results. W1–W3 enabled locally, mask 7.

## Open questions

- **Game time (§9).** Heading is `h11:08c28`, player x/y `h11:08c1c`/`08c20`;
  `h12:14b78` reads movement step `h12:0cdd6` when initializing actor speed.
  `docs/timing-investigation.md` maps a persistent 56-record actor table and its
  renderer-driven position/countdown updates; townsman identity remains open. The faster spin ends at a different heading
  with unchanged position; frame coupling remains. `tools/lov_state.py` maps visible-object
  render records but does not identify the townsman's world position. Deeper AI timing/state
  mapping remains open. W1/W2 retain existing timing; investigate a
  frame-rate-independent simulation step for movement, turning, animation and AI. Compare
  equal elapsed-field intervals across rendering rates, then evaluate elapsed-time scaling
  versus fixed ticks and A500 catch-up costs. See performance-plan §2.3.1 for the work plan.
- The conversation panel polls through h2, so `W` cannot wait for it; the route clicks EXIT
  blindly. A hook on its poll would make the route shorter.
- Entropy: the windows are identical across boots, so VPOSR reads do not leak into this
  route; re-check for any new route.

## Candidate optimisations (not started; plan in `docs/performance-plan.md`)

- Wall column drawer `h12:04c1a` and its setup `h12:02808`: ~38% of the A500 frame.
- Scaled sprites `h12:05114`: up to 13% when people are in view.

W7 (column-major layout and other later work) remains deferred by user decision.

W4 is committed: counted sprite rows on 68000/10, original loops on 68020+.
All three variants pass twins on both CPUs; final fixed-window A/B is in profiling §8.
