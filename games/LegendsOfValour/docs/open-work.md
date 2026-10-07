# Open work — Legends of Valour

Status 2026-10-07: playbook §1–§8 and W0–W6 complete. Fixed-window evidence
and commands are in `docs/profiling.md` §8. W2 uses MEMF_PUBLIC on every CPU;
W3–W5 select their replacements on 68000/10 and retain original code on 020+.
W6 improves the clear on both CPUs. W1–W6 are enabled in local preferences
(mask 63). Optional 25 Hz simulation timing and one-degree turning are implemented and
validated separately; both remain off in persistent preferences. W7 was dropped by user decision on 2026-10-07.

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

## Completed optional simulation timing

CUSTOM2 bit 6 implements the user-selected 25 ticks/second, historical mouse/
keyboard input, logical clocks, native pause/load boundaries and separate
native-cadence combat. Shared animation pacing retains the user-accepted fix.
Bit 7 independently enables one-degree turning. Preferences remain mask 63.

Both CPUs pass matched completed-tick comparisons for world/AI, movement,
turning, relative mouse input, collisions, animation, projectiles, daily events,
message pauses, save/load, manual/automatic combat and keyboard escape. Native
keyboard validation covers blocking reads, shift/repeat/ANSI, queue pressure,
shutdown and real save-name editing. All eight W1 off/on repeated-mode captures
pass, including negative heading wrap and no leaked motion at mode changes.

Equal elapsed-field observations and completed-tick comparisons have different
purposes: drawing can block world updates temporarily, then overdue ticks catch
up. The tests show no lost active time, but do not promise instantaneous state
identity or zero input latency. Maximum observed pending time in the deliberate
slow-drawing tests is 27 PAL fields (540 ms). The final spin and wall A/B on both
CPUs quantify the substantial A500 rendering cost. See profiling §8,
[timing investigation](timing-investigation.md) and [source audit](simulation-audit.md).

The normal interactive trial is launched in `tmp/playtest-simulation-final`:
28,375,160 Hz 68020, 2 MB chip/8 MB fast, PAL, normal blitter timing, warp off,
CUSTOM2=255. It uses the normal slave with no input tape or debugger. The
previous private trial had exited; amiga/.run and persistent preferences remain
untouched. Further subjective gameplay feedback is welcome, not an outstanding
automated validation gate.

## Open questions

- **Timing follow-up is implemented.** The investigation now includes the
  56-record actor map, clock/pause ownership, fixed ticks, native input/UI and
  both-CPU state/performance evidence. Remaining unknown scripted-purpose labels
  are identified as provisional; their native control flow is retained.
- The conversation panel polls through h2, so `W` cannot wait for it; the route clicks EXIT
  blindly. A hook on its poll would make the route shorter.
- Entropy: the windows are identical across boots, so VPOSR reads do not leak into this
  route; re-check for any new route.

## Completed rendering patches

- W3: fixed-displacement wall pairs on 68000/10; fixed-wall column cost falls 6.6%.
- W4: eight counted sprite rows on 68000/10; scanned-row costs fall 7.5–9.0%.
- W5: tagged exact-quotient cache on 68000/10; quotient costs fall 1.7–21.3%.
  All eight original continuations have runtime D7/CCR liveness guards.
- W6: backwards MOVEM clear on both CPUs; clear costs fall 38–39% on the
  A500 equivalent and 18–19% on the 020.
- Both-CPU VERIFY runs cover every wall/sprite block, every clear width,
  all three view geometries, all seventeen legal flag reads, and 262,140
  exhaustive reciprocal cases per CPU. Each feature has a separate source commit
  and final fixed-window A/B on both CPUs and both routes.
- Source audit: `docs/w3-w6-audit.md`; full evidence and timing limits: profiling §8.

W7 (column-major layout and other later work) was dropped by user decision on
2026-10-07; it is no longer an open work item.

Native capture blocking is resolved with the opt-in guest profiler handshake and
explicit PC-base normalization; see [native capture notes](native-capture.md).
Shared assets use ~/.local/share/amiga; projects are separate checkouts. ROM lookup
prefers shared files and retains verified fallbacks for ROMs not moved yet.


## Interactive evaluation

The requested normal trial is open with timing and one-degree turning enabled.
Its configuration and build hash are recorded in `simulation-audit.md`. Future
changes based on play feedback should retain the explicit timing toggle and
re-run the affected comparisons. W7 was dropped by user decision on 2026-10-07.

## One-degree turning

The user requested a plan for finer turning after accepting the walking-animation
correction. See [the one-degree turning plan](one-degree-turning-plan.md).
CUSTOM2 bit 7 now implements optional one-degree rendering and taps, with native
held-turn speed preserved after a 160 ms delay. Both-CPU automated table, full-angle
ray, legacy-pixel, input and allocation checks pass; profiling §8 records the cost.
Native save/load round trips pass on both CPUs; normal interactive evaluation
is the remaining acceptance step.
The one-degree source commit is separate from the simulation timing feature. W7 has been dropped.
