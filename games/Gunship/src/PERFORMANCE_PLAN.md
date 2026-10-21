# Gunship: performance analysis and plan for faster CPUs

Goal: make Gunship run smoothly on faster CPUs (68020–68060, fast RAM). Smooth means three
things here: game time runs at a fixed speed whatever the CPU, the frame rate goes up with the
CPU, and frames arrive at an even pace. The 68000 must keep working, but it is not the target.

Part 1 is the analysis the plan rests on. Part 2 is the plan. All code locations are offsets
into `gamemule` hunk 0 (`+xxxxx`, the numbering of the slave's patch lists). `Dxxxx` is an
offset into gamemule hunk 6 (data, also the `a4` base of the compiled C parts). `hN:xxxx` is
an offset into gamemule hunk N. ROM addresses (`$FCxxxx`) are Kickstart 1.3, which the slave
runs under KickEmu. This analysis covers the version handled by `pl_gamemule_658`.

## Part 1: analysis

### 1.1 How it was measured

Part 1 records the initial, uncontrolled measurements. The controlled baseline and
corrected measurement contract are documented under A below.

- **Route:** the shipped v1.2 slave runs under FS-UAE with a scripted keyboard and mouse route:
  1. Return in the intro.
  2. Vehicle identification: the top entry.
  3. Continue on the pilot, ops order, checklist and arming screens.
  4. In the cockpit, keys 1, 2 and 3.
- **Window:** 500 recorded fields over 524 elapsed fields (10.48 s PAL): each capture
  adds an unrecorded lead-in field. It covers the first take-off: F1 pressed ten
  times, then four 100-field captures. A corrects this to 500 elapsed fields.
- **68000 instrument:** cycle-exact Barto traces (FS-UAE gdb stub). The machine is an A500 with
  512 KB chip RAM and 8 MB fast RAM.
- **68020 instrument:** the same trace, on an A1200 with 2 MB chip RAM and 8 MB fast RAM.
- **68030/040/060 instrument:** AmigaXDev's exact per-PC cycle profiler (aprof), on cycle-exact
  cores without an MMU model:
  - 68030 at 50 MHz,
  - 68040 at 25 MHz,
  - 68060 at 50 MHz,
  - all on the same A1200 base.
- **Reproducibility:** two boots of the route gave identical instruction records.
- **Caveat: the mission differs between machines.** The game picks it with a timing-dependent
  random choice, so each CPU gets a different mission. Cross-machine numbers therefore compare
  similar take-offs, not identical scenes; the completed A2 baseline fixes this. The 68040 and 68060 runs happen
  to fly the same mission.

### 1.2 Program structure

`gamemule` is the flight program. `titlmule` and `scrnmule` (intro and menus) are not
involved in the flight.

- **Game code:** a mix of compiled C (small data through `a4`) and hand-written assembler with
  absolute addressing (globals through `a5` = `D38F6`). Code, globals and tables are all in
  fast RAM; every drawing target is in chip RAM.
- **Display:** one Intuition screen, 320×200, 5 bitplanes. There are five 320×200×5 bitmaps in chip
  RAM:
  - 0 and 1: the double buffer,
  - 2 to 4: source art (map, cockpit, symbols).
  - There is also a single-plane mask/TmpRas bitmap.
- **What is redrawn each frame:** the cockpit is copied into both display buffers once at mission
  start. After that only the 3D view (320×90) and the instruments that changed are redrawn.

**Simulation tick loop, `+0563A`.** Each pass runs one simulation tick:
- the tick counter `D3B94` +1,
- controls and the flight model,
- `+04288`, which renders,
- `+04E3C`, keyboard commands,
- `+0937C`, `+0979C`, `+09C5C`, `+09F74`: AI, weapons, damage,
- every 16th tick, `+07F80`.

**Render between ticks, `+04288`.** It renders `ceil(D1548 / D154A)` frames per tick. With the
shipped values 6 and 3 that is 2 frames:
- the first is interpolated half-way between the previous and the new state,
- the second is drawn at the new state.
- Interpolated: the camera (position, altitude, heading, pitch, roll), six effect objects and the
  instrument values.
- Every other world object moves only once per tick.

**Frame, `+05C04`**, in order:

| step | routine | work |
|---|---|---|
| 1 | `+084E2` | point the RastPort at the back buffer (`D4BB0` is the back-buffer index) |
| 2 | `+07A1C` ×2 | sine of roll and pitch |
| 3 | `+05F8E` | choose the 3×3 terrain cells for the heading octant |
| 4 | `+05CBE`/`+05D62` | build the per-axis premultiplied rotation tables |
| 5 | `+05EA4` | rotate the shared vertex palette (111 + 35 vertices) by table sums |
| 6 | `+077B8` | clear the view by painting sky and ground bands (`+0921C`), horizon wedge and line, attitude ball (`+090DA`) |
| 7 | `+060A8` | the 3D view (§1.4) |
| 8 | `+0468C` | moving map (re-checked every 8 frames, blitted on change) |
| 9 | `+06224` | effect objects (explosions) |
| 10 | `+0AA4C` | cockpit: overlay restore, readouts, needles, gunsight, TADS scope, tapes, bar gauges |
| 11 | `+09B9A`, `+0BE5A`, `+0A37C`, `+0BE2C` | effect spawn and animation, tracers, centre message |
| 12 | `+04496` → `+00B7C` | swap: Intuition MakeScreen + RethinkDisplay |

**VBL server, `+00F14`** (exec AddIntServer, pri −60). Every field it:
- increments the VBL counter `h2:001C`,
- runs `+04B48`: sound, timers, palette flash, sprites, the music driver,
- reads the joystick and mouse (`+01068`).

### 1.3 Game time (answer to "faster or smoother?")

**On a faster CPU the game runs faster.** It does not just run smoother.

- **One fixed step per tick.** Each tick advances the simulation by a fixed step, and a tick
  always renders 2 frames. Nothing scales the step by elapsed time.
- **Elapsed time is measured but thrown away.** `+04470` measures the VBLs elapsed per tick
  and passes them to `+02276`. That routine computes a frame rate, assuming 60 Hz, and the
  result is discarded.
- **No game code limits the frame rate.** The only wait is the WaitTOF inside Kickstart 1.3's
  RethinkDisplay. Frame times therefore round up to whole fields, with a hard limit of 50 fps
  (25 ticks/s).
- **timer.device is opened but never used.** It is opened at `+032A4` (UNIT_VBLANK) and never
  sent a request. The game reads no beam position, CIA timers or DateStamp.

Measured in the take-off window, in simulation ticks per second of emulated time:

| machine | fps | ticks/s | game speed vs A500 |
|---|---:|---:|---:|
| A500 (68000) | 5.3 | 2.7 | 1.0× |
| A1200 (68EC020) | 14.8–15.1 | 7.5 | 2.8× |
| 68030/50 (heavier mission) | 10.0 | 5.1 | 1.9× |
| 68040/25 and 68060/50 | 15.2 | 7.5 | 2.8× |

Even on the A500 a tick takes 16–20 fields depending on the scene, so game speed already
varies with what is on screen.

**What stays at real-time speed**, because the VBL server runs it per field:
- sound and music,
- warning-lamp blinking,
- the hit flash and the effect-spawn window `D42F7`,
- tracer cadence (`+0A37C`, at most every 4 fields),
- stick input accumulation.

**Per rendered frame instead of per tick:**
- bar gauges move 1 pixel per frame (`+0ADB6`),
- one effect spawns per frame while `D42F7` ≠ 0,
- the map is re-checked every 8 frames.

**The key with raw code 12 doubles game speed at the same frame rate.** Its handler at `+04EF2`
toggles `D1548` between 6 and 3, which switches the interpolated frame off.

### 1.4 How the 3D view is drawn

**Cell walk, `+060A8`.** It walks the 3×3 cells around the helicopter in two passes, in a fixed
cell order for each heading octant. There is no depth sort: painter's order comes from the cells,
then from object order within a cell.

**Per object, `+0625C`.** The position comes from palette vertex sums (table adds, no multiplies).
Then:
- cull against Z, the frustum and distance,
- pick the level of detail,
- draw the shape with `+063DC`.

**`+063DC`, per shape:**
- transform and project the vertices: `+06642`/`+066E8`, 2 `divs` each, roll applied as a shear;
- backface flags: `+06818`;
- near-plane clip and an edge cache: `+06792`;
- run the shape's primitive list.

**Lines.** `+08538` clips with Cohen–Sutherland (`+082EC`, `+08466`). Then `+08548` draws with
the blitter in line mode, one blit per bitplane. A plane whose colour bit is 0 still costs a blit,
with a clear minterm.

**Convex polygons:**
- `+08698`/`+089E4` build a per-scanline span table in fast RAM.
- `+08B6C` writes the spans into the single-plane chip mask with the CPU, then makes one masked
  blit per plane.
- `+08818` clears all 200 span rows for every polygon, although the view has 90, and
  blitter-clears the previous mask box.

**Frame clear.** `+0921C` blitter-fills the whole 320×90 view in 5 planes, as a sky band and a
ground band.

**Volume:** about 18 shapes, 112 vertices, 58 lines and 12 polygons per frame in the A500 window.
That makes about **250–300 blits per frame**.

**How the blitter is driven.** The game owns the blitter for the whole flight: OwnBlitter at
`+0867C`, DisownBlitter at `+0868C`. It writes `$DFF040–$DFF074` directly. Every blit is preceded
by a busy-wait on DMACONR BBUSY.

### 1.5 Where the time goes

**68000 (A500 machine, 142 101 cycles per field, 9–10 fields per frame):**

| bucket | share of all cycles |
|---|---:|
| 3D view `+060A8` (inclusive) | 42.0 % |
| sky/ground, horizon, attitude ball `+077B8` | 8.5 % |
| cockpit `+0AA4C` | 8.6 % |
| swap `+04496` (MakeScreen, RethinkDisplay; mostly ROM) | 4.5 % |
| vertex rotation `+05EA4`, axis tables `+05CBE` | 4.3 % |
| moving map `+0468C` | 1.4 % |
| simulation tick (outside rendering) | ≈1–2 % |
| supervisor: level-3 interrupts (BLIT ≈10–11 %, VERTB ≈9 %) | 19.7 % |
| exec STOP idle (the WaitTOF in RethinkDisplay) | 4.6 % |

Across these buckets, about 21 % of all cycles are the CPU spinning in the BBUSY wait loops. The
geometry work (transform, projection, culling, clipping) is about 19 %.

The hottest instructions are the BBUSY polls themselves:
- `+08626`/`+0862C` in the line drawer: 7.4 %
- `+09242`/`+09248` in the band clear: 5.5 %

**68020 to 68060 (aprof, % of all clock units):**

| machine | fps | BBUSY spin | level-3 interrupts | swap incl. VBL wait | geometry (self) | idle |
|---|---:|---:|---:|---:|---:|---:|
| 68EC020/14 | 15.1 | 43.6 % | 17.6 % | 15.0 % | 10.6 % | 10.2 % |
| 68030/50 | 10.0 | 45.1 % | 16.7 % | 12.1 % | 9.1 % | 9.5 % |
| 68040/25 | 15.2 | 68.9 % | 5.3 % | 11.1 % | 1.5 % | 10.1 % |
| 68060/50 | 15.2 | 68.9 % | 5.3 % | 11.1 % | 1.5 % | 10.1 % |

**From the 68020 on, the game is limited by the blitter.**
- The 68040/25 and 68060/50 produce identical profiles, frame for frame: CPU speed no longer
  changes anything.
- On the 68060 a frame, about 3.3 fields (66 ms), splits into:

  | part | routine | share | what dominates |
  |---|---|---:|---|
  | 3D view | `+060A8` | 34.5 % | polygon blits `+08B6C` 18.7 %, line blits `+08538` 11.7 % |
  | background | `+077B8` | 27.0 % | band clear `+0921C` 22 % |
  | cockpit | `+0AA4C` | 21.3 % | re-blitting the cockpit frame over the view, `+0AA80`, 11.5 % |
  | swap | `+04496` | 10.8 % | almost all of it the wait for the next vertical blank |

  Nearly all of the first three is BBUSY spinning.
- Blitter busy time is about 51 ms per frame on the A500 and about 59 ms per frame on the
  68EC020. That caps this scene at about 15–16 fps on any CPU, as long as the blits stay as they
  are.

**Per-blit interrupts do nothing useful.**
- Graphics.library leaves INTENA.BLIT enabled, so every game blit ends in a level-3 interrupt.
  That is about 28–57 per field.
- Each one goes through exec's dispatcher (`$FC0D14`) and the graphics blitter handler
  (`$FC6DFA`), which finds no QBlit queue, and exits through KickEmu.
- That costs about 520 cycles per blit on the 68000. It lands exactly between two blits, while the
  CPU waits to start the next, so it lengthens the blitter's critical path on every CPU.

**The swap is expensive.**
- MakeScreen + RethinkDisplay rebuild the copper lists every frame: about 8 ms per frame on the
  68000.
- RethinkDisplay then waits for the next vertical blank, so drawing never overlaps the wait.
- The swap also spins until the game's screen is in front (`+00B86`), and copies an unchanged
  palette.

### 1.6 Hazards on faster CPUs

These are the original game's hazards. B1/B2 now fix the waits and pixel
ordering; B3's data/code audit is in [CACHE_AUDIT.md](CACHE_AUDIT.md).

- **BBUSY read too early.** Every BBUSY wait reads DMACONR once, one to three instructions after
  writing BLTSIZE: `+02D84`, `+02EFA`, `+030C6`, `+0319A`, `+031E6`, `+08626`, `+088D8`,
  `+08BD6`, `+08D3E`, `+08D7A`, `+09198`, `+09242`, `+092F6`, `+0933C`.
  - On a 68020 or faster the first read can see BBUSY still clear. The next blit's registers, or
    the CPU's mask writes in `+08B6C`, can then hit a blit that is still running.
  - Kickstart reads DMACONR twice for this reason.
  - This was inferred from the code; no corruption has been observed yet.
- **Pixel writes without a wait.** `+0828A` (pixel plot) read-modify-writes chip bitplanes without
  waiting for the blitter.
- **Code, tables and caches.** Tables and vertex buffers live inside the code hunk (for example
  `+06ACA`–`+07592`, `+08D88`). They are written as data only, and no self-modifying code was
  found. B3 confirms that the writable islands are data, not instructions;
  chip DMA memory is non-cacheable and fast CPU-only data may use copyback.

## Part 2: plan

The order follows the goal. B makes fast CPUs safe. C fixes game speed: this is the change
that makes fast CPUs play correctly. D and E raise the frame rate, which on 68020+ means less
blitter work. Each step is one commit. After each, measure with the instruments of §1.1 and
compare state as described in A4, before going on.

### A. Measurement base

**Status: complete (A1–A5).** The source rebuild and VERIFY-only fixed-seed,
completed-frame log and tick-checkpoint instruments are validated for version 0658.
CUSTOM2=0 applies no diagnostic patches; a nonzero CUSTOM2 selects the seed.
CUSTOM3=1 additionally selects an authored combat starting position, with three
ground targets and an existing enemy helicopter initially in view. Normal builds
contain none of these instruments and are byte-identical to the initial rebuild.
The shipped/rebuilt difference is fully accounted for: 160 bytes in the shared
SDK prefix, 72 bytes of date strings, and twelve validated symbol relocations in
an otherwise identical 780-byte game-specific tail.

The five-CPU take-off matrix and the 68000/060 hover and combat windows pass,
each over exactly 500 game VBLs. Two independent boots have byte-identical entire
8 MiB fast-RAM snapshots at ticks 100–102; neighboring ticks differ, including
player state with the tick counter excluded. Seed 1 selects the same mission on
all five CPUs and with extra menu delay; seed 2 changes it. The 8192-row bounded
swap log passes 128 register/CCR/overflow cases and agrees with continuous aprof
swap counts on 020+. Barto's omitted fields are explicitly accounted for.

Build and acceptance commands, fixture details, hashes and raw evidence live in
`tmp/dev/docs/measurement-a.md` and `tmp/dev/tmp/a-final/` (ignored harness).
`tools/compare_states.py` supplies A4's regression gate; matching simulation state
across CPUs remains an acceptance requirement for the future C changes. A itself
introduced no B–G performance or game-time changes.

Measurement correction: the original multi-capture route advanced 524 VBLs, not
500, because each emulator capture includes an unrecorded lead-in field. New
measurements assert 500 actual game VBLs and use the continuous completed-swap
log for fps and pacing. Barto percentages describe its recorded sample; aprof
covers the full window on 68020+. With seed 1, completed fps are 5.1 / 10.5 / 10.9 /
15.3 / 15.3 on the 68000 / 020 / 030 / 040 / 060 configurations above. The historical
uncontrolled numbers in Part 1 are motivation, not the controlled baseline.

| Window | 68000 fps / ticks/s | 68060 fps / ticks/s | Frame interval (VBLs), 68000 / 060 |
|---|---:|---:|---:|
| Take-off | 5.1 / 2.5 | 15.3 / 7.6 | 9–10 / 3–4 |
| Hover | 5.5 / 2.8 | 16.7 / 8.4 | 9–10 / 3 |
| Ground attack | 5.3 / 2.7 | 16.6 / 8.3 | 7–13 / 2–4 |

These are the instrumented emulator baseline, not hardware performance claims.
The combat window averages 19.3 full shapes/frame on the 060 versus 14.0 in
take-off. Its AI remains active, so the helicopter can leave the view.

- **A1. Rebuild the slave from source.**
  - A1a. Build `GunshipHD.s` with vasm against the current WHDLoad includes, using kick13.s.
  - A1b. Compare the result with the shipped v1.2 `Gunship.slave`, and explain every difference
    (date string, include versions).
  - A1c. Keep the build output out of the tracked tree.
- **A2. VERIFY build with a fixed mission.**
  - A2a. Find the random number generator and its seeding. The mission choice depends on input
    timing (the ops order changes with the route's click timing).
  - A2b. Add a VERIFY-only CUSTOM option that fixes the seed, so every CPU flies the same
    mission and scene.
  - A2c. Re-measure the §1.5 matrix with it.
- **A3. Benchmark windows.**
  - A3a. Keep the take-off window of §1.1.
  - A3b. Add a busier window: ground attack with several targets in view, and an enemy
    helicopter.
  - A3c. Add a hover window with little on-screen change.
  - A3d. Record fps, ticks per second and per-frame field timestamps, so pacing jitter can be
    measured as well as the average.
- **A4. State comparison.**
  - A4a. Snapshot the simulation state (`D3B88`… player block, object tables, the clocks of
    §1.3) when the tick loop `+0563A` completes a tick.
  - A4b. Check that two boots compare equal and that different ticks do not.
  - A4c. Use the comparison for every change in C: matched ticks must compare equal across
    CPUs once C is in.
- **A5. Frame log.**
  - A5a. Add a VERIFY-only log of (VBL counter, tick counter) at each swap, kept in slave memory.
  - A5b. Read the log with the read-only debugger.
  - A5c. This works on the 68030 and up, where Barto traces are empty, and it measures pacing.

### B. Correctness on fast CPUs

**Status: complete (B1–B4).**

**B1/B2 complete.** `blitter.i` validates all 14 `BTST/BNE` loops (12 using
a0, one a1, one a6) and the unique pixel-write helper call before modifying the
loaded game. It replaces each loop with `JSR/NOP` and wraps the pixel helper
with the same double-read wait. Registers and the original wait's CCR effects
are preserved. The master CUSTOM1 **Enhanced framerate** option now gates
these patches on all three recognised gamemule paths.
Instruction signatures avoid assuming a common offset delta between releases.
Any missing, additional or malformed match aborts before patching.

PAL 0658 and NTSC 1489 binaries pass assembled dispatcher tests; malformed
layouts are rejected without partial writes. Delayed-BBUSY and all 32 CCR
combinations pass. PAL flight smoke checks pass on 68000 and 68060. The German
dispatch path is exercised with relocated fixtures, but an original German
binary has not yet been tested; its runtime signature checks remain mandatory.

**B3 complete.** [CACHE_AUDIT.md](CACHE_AUDIT.md) inventories all writable hunk-0
islands, including indirect stores. The audit accounts for 267 direct write
sites at 138 destinations and finds no overlap with executable instructions.
The existing `CACHE` policy is appropriate: non-cacheable chip/base memory,
copyback fast/slave memory, and a flush after LoadSeg callbacks finish patching.
No additional runtime flush or data relocation is needed. VERIFY records the
load-time cache policy and exposes a completed-swap checkpoint with the tick
in a CPU register, avoiding stale debugger reads of copyback data.

**B4 complete.** All 21 completed-frame captures match byte-for-byte across
40,000 displayed bitplane bytes and the 64-byte palette: nine A2 cycle-exact
68020/68040/68060 samples at ticks 100/110/120, plus twelve cache-functional
samples at ticks 300/310/320 (68020, full-MMU 68040/68060, and 68040 NOCACHE).
The latter use CPU-observed ticks and buffer selection; physical RAM can lag
copyback data. Cache-on policy is `0x3b3d`; the NOCACHE control reports zero.
The full-MMU cache checks use immediate blits because the asynchronous-blitter
emulator configuration reproduces cockpit corruption with both the pre-B slave
and NOCACHE. They validate cache correctness, not blitter timing or performance;
timing coverage comes from the cycle-exact runs and delayed-BBUSY tests.

The 180 assembled blitter cases and 128 frame-hook cases pass, as does a
SetCPU scratch-register preservation test. PAL 68000/68060 flight and 68060
combat smoke checks pass. NTSC 68060 reaches flight with all 14 waits patched,
using a live-pilot roster only in its disposable runtime copy. All 226 original
PAL, installer and NTSC files remain unchanged. Evidence and reproducible commands
are retained in the ignored harness (`docs/measurement-b.md`,
`tmp/b/acceptance.json`). Original German and real-hardware coverage remain
release limitations, not implied by these emulator checks.

- **B1. Safe blitter waits.**
  - B1a. Replace the 14 BBUSY loops of §1.6 with a slave routine that does a dummy DMACONR read,
    then the BBUSY loop. Patch each with `PL_PS`/`PL_P`, keeping the loop's register use.
  - B1b. Add a wait to `+0828A` before its read-modify-write.
- **B2. Apply B1 for every CPU when Enhanced framerate is enabled.** The cost on the 68000 is a few cycles
  per blit. Patch the other two supported versions (`gamemule_1489`, `gamemule_german`) at their
  matching offsets.
- **B3. Cache audit.**
  - B3a. List all writes into hunk 0, and confirm none of them is ever executed.
  - B3b. Confirm the slave's `CACHE` setting suits the 68040/68060 with copyback.
  - B3c. Fix with flushes or by moving data only if the audit finds a problem.
- **B4. Validate.** With the A2 seed, run the 68040/68060 and compare screenshots at matched
  ticks with the 68020: the picture must be identical.

### C. Game time independent of frame rate

This follows AmigaXDev `docs/playbooks/fixed-time-simulation.md` and
`simulation-and-presentation.md`. The design is the hybrid used in Wing Commander, where
the world kept its intended 10 Hz and the player's own motion became responsive (that
project's `docs/timing-design.md`, design D, and its phase-9 gate in `docs/internals.md`).

**Refocus (2026-10-21, user decisions).** These override the open-ended
acceptance text in the status notes and items below where they conflict.

- **68020 and up only.** On a 68000, Enhanced framerate is ignored and the game
  keeps native timing; the ReadMe says so. The 68000 renders about 1 fps, so a
  3 Hz world cannot make it smooth. 68000 rate, overload and responsiveness work
  stops. Keep the existing cross-CPU state comparisons as regression checks.
- **Simple object prediction (C6).** Every world object is drawn with bounded
  forward extrapolation from its last committed motion, at most one tick
  ahead, snapping at spawn, impact, slot reuse and lifecycle changes. The exact
  guided-forecast path (private scene collection, selector certification,
  forecast tapes) goes behind a disabled assembly flag or is removed. G stays
  the fallback if play shows visible errors.
- **Exit criteria for C**, replacing the full C9 matrix as the release gate:
  1. World rate 3.00 Hz ±1 % on 68020 and 68060, PAL and NTSC, in ordinary play.
  2. Held-input player state at world ticks equals native (already shown).
  3. Input shows on the next completed frame.
  4. Enhanced fps is no lower than native fps in the same scene.
  5. The user plays a full mission on the a1200 and the 68060 with no visible
     problems.

  Remaining C9 items become regression checks or later notes, not blockers.

**Steps, in order; stop and report after each.**

1. Freeze: no new forecast, certification or 68000 work.
2. Measure ordinary play from normal startup on a1200-fast and 68060, CUSTOM1
   off and on, same window: fps, world Hz, input-to-frame delay.
3. Simplify per the decisions above. Profile what CUSTOM1 adds on the 68020
   and cut it until criterion 4 holds.
4. Provide a windowed a1200 configuration with CUSTOM1=1 for the user to play;
   fix only what the user reports.
5. List at most ten release blockers; everything else is a later note.
6. Trim this section's status notes to about 20 lines and make
   `TIMING_DESIGN.md` describe the current design; history is in git.
7. Then D2 (D1 brought forward into step 3 by user approval), then E1: C fixes speed and response, but the blitter caps
   drawing at about 15 fps until D and E.

**Current status (2026-10-21): refocus step 7 complete: D2 and E1 are implemented.**
Enhanced mode ships in the 2.0b slaves for 0658 and 1489, gated by
CUSTOM1 on 68020+; C remains open against the five exit criteria above.
Held-input native endpoint equivalence (criterion 2) is shown.
Step 3 met fps parity (criterion 4): 020 10.4 → 11.5; 060 16.3 → 16.7 fps.
Step 7 PAL 500-field window: enhanced 020 11.7 fps, 060 25.0 fps; both 3.00 Hz.
Next-completion delays: 020 median 60 ms (20–80), 060 20 ms in all eight samples.
F normal-startup windows meet 3.00 Hz on 020/060 in PAL and NTSC (C-R2 complete).
Input-to-completion medians were 60/40 ms; visible response still needs confirmation.
Reported ground-gauge, 68040 BltClear, damage-yaw and deferred missile-kill fixes are in.
Small-bank left/right asymmetry is native handling and is retained.
Full-mission user acceptance remains open; targeted checks do not replace it.
Unattended demo playback and any-key exit are confirmed enhanced-mode regressions.
Current ownership, source map, evidence and demo diagnosis: [TIMING_DESIGN.md](TIMING_DESIGN.md).

**Release acceptance items (four open; authoritative list from step 5).**

| ID | Remaining work | Completion evidence |
|---|---|---|
| C-R1 | Restore unattended demo playback and any-key exit. | Normal startup without input flies the recorded demo; a key exits as with CUSTOM1=0. |
| C-R2 | Complete: ordinary-play world rate on 68020/68060, PAL/NTSC. | F release-slave 500-field windows each measured 3.00 Hz (criterion 1). |
| C-R3 | Confirm visible response to new input. | The response appears on the next completed frame (criterion 3). |
| C-R4 | Full-mission user acceptance on a1200 with current fixes. | No visible problems, including missile destruction and damaged-tail-rotor motion (criterion 5). |
| C-R5 | Full-mission user acceptance on 68060 with current fixes. | No visible problems (criterion 5). |

**Work-item reference.** IDs are retained for navigation; this is the current
scope, not a second release checklist. Historical implementation reports are
in git. C9's wider matrix is regression material, and the T-74 graphics report
is a later verification note. No further 68000 timing or exact-forecast work.

- **C1. World clock.**
  - C1a. Keep the native elapsed-time conversion: three ticks make one second.
  - C1b. Schedule 3 ticks per 50 PAL or 60 NTSC display fields: 17/17/16 or 20 fields.
  - C1c. Preserve native world constants and clock conversion.
- **C2. Scheduler.**
  - C2a. Accumulate three clock units per active field; consume one display-rate quantum per tick.
  - C2b. Consume field history and due world work before drawing the latest pose.
  - C2c. Count active game fields only.
- **C3. Field-stamped input.**
  - C3a. Retain controls, buttons, edges and command positions in a bounded history.
  - C3b. Consume every retained player record once, in order.
  - C3c. Retain world input until its deadline without applying player motion twice.
  - C3d. Preserve native input filtering and command semantics; demo exception is C-R1.
- **C4. Player motion.**
  - C4a. Keep the field/writer inventory in [PLAYER_STATE_INVENTORY.md](PLAYER_STATE_INVENTORY.md).
  - C4b. Separate continuous motion from world-owned reserves, damage, weapons and contact.
  - C4c. Distribute interval-anchored native motion contributions across delivered fields,
    recomputing with fresh controls and retaining fractional state.
  - C4d. Preview native flight arithmetic on private state.
  - C4e. Preserve bit-exact native endpoints for held input; within-tick changes contribute
    immediately and need not equal a native tick that never sampled them.
  - C4f. Keep the exact-input motion cache; further 68000 pricing is retired by the refocus.
  - C4g. Draw camera and instruments from current field state; advance gauge slew per field.
  - C4h. Exclude already-consumed player motion from native world execution.
- **C5. Player/world hand-off.**
  - C5a. World logic reads the latest authoritative player state at its deadline.
  - C5b. Ground/object contact remains a world-tick decision using native semantics.
  - C5c. Selected option (a): latch triggers and launch at the next world tick,
    from that tick's pose (up to 333 ms). Trigger-field launch prediction is deferred.
  - C5d. Commit targeting at world deadlines; current-view aiming graphics cannot change locks.
- **C6. World-object presentation.**
  - C6a. Extrapolate consecutive committed motion by at most one tick, renderer-only.
  - C6b. Track generation/type/lifetime so reused slots cannot inherit old motion.
  - C6c. Snap at discontinuities and lifecycle changes; never feed predictions into gameplay.
  - C6d. Exact guided forecasting is removed from the runtime. Consider G only if play
    demonstrates that bounded prediction is inadequate; no further certification work.
- **C7. Work formerly tied to drawing.**
  - C7a. Spawn effects at world ticks; consume animation/countdown progression per field.
  - C7b. Evaluate the renderer-derived contact/flight-end result on committed world geometry.
  - C7c. Refresh map coordinates after consumed player fields.
  - C7d. Retire native speed-toggle command 12 in enhanced mode without resetting clock phase.
  - C7e. Keep per-buffer dirty/repaint counters drawing-owned.
- **C8. Catch-up and lifecycle.**
  - C8a. Consume overdue fields/worlds with a bounded catch-up allowance.
  - C8b. Yield to drawing without discarding ordinary backlog; account for exceptional
    excess recovery. Suspend/rebase around pause and native modal work, with no paused-time debt.
  - C8c. Invalidate player/prediction history on lifecycle transitions and flight retirement.
- **C9. Validation reference; only the five refocus criteria are release gates.**
  - C9a. Existing cross-CPU and drawing-independent state comparisons remain regression checks.
  - C9b. Ordinary-play world-rate acceptance is C-R2.
  - C9c. Visible next-frame input response is C-R3; full-mission play is C-R4/C-R5.
  - C9d. Retain native held-input player endpoint checks (criterion 2 already shown).
  - C9e. Retain clock, reserves, reload, effect and lifecycle duration checks.
  - C9f. Retain bounded-prediction/identity checks; do not restore exact-forecast gates.
- **C10. Option.** All framerate enhancements use default-off **Enhanced framerate**
  (CUSTOM1). Below 68020 the option is ignored. Existing baseline cache policy and
  compatibility/protection fixes remain baseline behavior. Future D/E work shares this gate.

### D. Remove fixed overheads

**Status: complete for the enhanced 0658 runtime (2026-10-21).**
D1–D3 and D5 are complete; D4 is closed by user decision. Other executable
versions remain F2. This does not close C's five release blockers.

- **D1. Blitter interrupt off during flight — complete for the experimental 0658 runtime.**
  Brought forward into refocus step 3 with user approval; results and ownership
  restoration check are recorded above. Other executable versions remain F2.
  - D1a. After OwnBlitter (`+0867C`), save INTENA and clear BLIT. Restore it before DisownBlitter
    (`+0868C`).
  - D1b. Check that nothing queues QBlit work during flight.
  - D1c. Expected gain: most of the level-3 time, which is 5 % (68040/060) to 17 % (68020) of all
    time and includes the one VERTB per field. On top of that it removes about 520 cycles of
    blitter idle between consecutive blits.
- **D2. Cheap buffer swap — complete for the enhanced 0658 runtime.**
  `timing-display.i` patches the flight swap only; modal/native calls still rebuild.
  The VBL exchanges ten bitplane-pointer words and acknowledges before buffer reuse.
  Palette moves remain in place; FrontScreen waiting yields through WaitTOF.
  A1200 normal-startup/takeoff smoke passed with no input loss or scheduler fault.
  A 100-field moving-flight profile completed 25 swaps (12.5 fps), with zero
  calls to +00B7C/MakeScreen/RethinkDisplay and 0.38% task-side swap self time.
  This short window is not a matched-scene overall speed comparison. Evidence:
  ignored `tmp/dev/tmp/step7-d2-smoke/` and `step7-d2-profile/`.
  - D2a. Replace MakeScreen + RethinkDisplay in `+00B7C`. Build the screen's copper list once,
    then exchange the bitplane pointers for the two buffers, by patching the BPLxPT moves or by
    using two prebuilt copper lists.
  - D2b. Make the exchange in the game's VBL server, so the change happens at a vertical blank.
  - D2c. Keep the palette pokes that `+00AB8` locates (flash effects).
  - D2d. Drop the palette copy that changes nothing.
  - D2e. Keep the front-screen check, but stop spinning on it.
- **D3. Don't wait for the vertical blank — complete for enhanced 0658.**
  Swaps publish and return; bitmap binding waits for VBL acknowledgement before
  reusing a displayed buffer. Native swaps and DisownBlitter drain pending work.
  VERIFY timestamps the actual VBL exchange. Existing 500-field PAL windows:
  020 12.4 fps, 060 25.0 fps, both 3.00 Hz; pause/exit cleanup passed.
  Evidence: ignored `tmp/dev/tmp/d3-{fps020,fps060,pause-exit}/`.
  - D3a. With D2, the task requests the swap and continues.
  - D3b. Before drawing into a buffer it waits only until that buffer is no longer displayed.
- **D4. Triple buffering — closed, declined by the user (2026-10-21).**
  Keep D3's asynchronous double buffering. The uncommitted triple-buffer
  implementation was removed; no third bitmap or triple-buffer option ships.
  - D4a. Third chip bitmap: cancelled.
  - D4b. Drawing/display overlap through a third buffer: cancelled.
- **D5. Small fixes — complete for enhanced 0658.**
  - D5a. Removed the final wait at `+08D7A`, preserving its return flags.
    Consumer waits before mask/pixel access, blitter setup and display publication remain.
  - D5b. Clear only the previous polygon's inclusive, clipped span rows, in both
    CPU and native paths. Initialize all 200 rows once; clear pending rows before
    the native text path resets the shared bounds. CPU/native view comparison:
    173 takeoff/banking frames, zero differing words across 18,000 bytes/frame.
  - D5c. Measured BLTPRI with the existing 500-field PAL flight window. Normal /
    priority: 020 **12.5 / 12.7 fps**, 060 **25.0 / 25.0 fps**; all **3.00 Hz**.
    Retain the incoming priority: the small 020-only gain in this short window
    does not justify changing bus arbitration. Priority remains a diagnostic experiment.
  First-use initialization, clipped/empty span ranges, guards/registers and all
  32 return-flag combinations passed. Full-MMU 040 CACHE startup/takeoff and
  native pause/exit with blitter-interrupt restoration passed. The ordinary slave
  remains byte-identical. Evidence: ignored `tmp/dev/tmp/`
  `d5-initialized-pixels/`, `d5-final-{fps020,fps060,priority020,priority060}/`,
  `d5-040-cache/` and `d5-pause-exit/`.

### E. Cut blitter work (the ceiling from the 68020 on)

**Complete for enhanced 0658 (2026-10-21).** E4 is closed by the user-approved
measurement decision. Other executable versions remain F2; C-R1–C-R5 remain open.

- **E1. CPU renderer for the 3D view — complete for the enhanced 0658 runtime.**
  `timing-cpu-render.i` retains native geometry/clipping and draws the view into
  an 18,000-byte MEMF_FAST buffer: pen-selected multi-plane Bresenham lines,
  direct word spans, and MOVEM sky/ground fills. Five planes are copied once
  before the native cockpit overlay. Allocation failure keeps native drawing.
  Same-state CPU/blitter comparison passed across 163 takeoff/banking frames
  (all 18,000 bytes/frame); the native polygon right-edge word-boundary quirk
  is preserved. Normal full-MMU 68040 CACHE startup/takeoff also passed.
  Existing 500-field PAL measurement: 020 117 frames (11.7 fps), 060 250 (25 fps),
  both 30 world ticks (3.00 Hz). These are short play windows, not full missions
  or the outstanding PAL/NTSC acceptance. E1 adds no release gates.
  Evidence under ignored `tmp/dev/tmp/`: `step7-e1-pixels3/`,
  `step7-e1-fps020/`, `step7-e1-fps060/`, `step7-e1-040-cache/`.
  Focused allocation/fallback checks passed; ordinary slave is byte-identical.
  - E1a. Draw the 320×90 view, 4 planes plus plane 4 where needed, into a fast-RAM planar buffer
    with the CPU:
    - Bresenham lines that set all colour bits in one pass, instead of one blit per plane,
    - direct span fills for polygons, with no mask plane,
    - `movem` fills for the sky/ground bands.
  - E1b. Copy the finished view into the chip back buffer once per frame: about 14–18 KB, a few
    ms.
  - E1c. Select it when the CPU is a 68020 or better and fast RAM exists, and keep the blitter
    path for the 68000.
  - E1d. The result must be pixel-identical to the blitter path at matched ticks (A4/B4).
- **E2. Cockpit overlay — complete for enhanced 0658.**
  - E2a. Audited the three restores: top view strip, right view strip (which
    wraps one word into the following row), and attitude-instrument bezel.
  - E2b. The CPU copy leaves the opaque top five rows untouched and composes
    the two edge words of each remaining view row using bitmap 3's plane-4
    mask and cached artwork. The middle uses MOVEM. The first two restores
    are skipped; the bezel below the view remains native. Keep rectangular
    fills in fast RAM and the native fallback without an allocation; no new
    68000 path work. View plus art cache uses 36,010 fast bytes. Native screen
    swaps and module installation invalidate the art cache.
- **E3. Remaining cockpit blits — complete with targeted update suppression.**
  - E3a. Current 060 profiling measured needle erase/draw at about 2.9%, scope
    at 2.3%, and tapes at 1.7% before this work. Text, scope and tapes retain
    native drawing and their existing conditional updates.
  - E3b. `timing-cockpit.i` retains unchanged needles independently in each
    back buffer, skipping both erase and redraw. Native screen swaps and
    pending panel restores invalidate the cache: the rotor-warning panel
    overlaps a needle. Modal/native ownership and allocation failure retain
    native behavior. No full cockpit CPU renderer is introduced.
  Same-state native redraw comparisons passed: **423 edge frames, 95 skipped
  needle frames, zero differing words**. Two-buffer/change/panel/modal cache
  checks and allocation fallback passed. Full-MMU 040 CACHE startup/takeoff,
  pause/exit and blitter-interrupt restoration passed. Ordinary slave is
  byte-identical. Evidence under ignored `tmp/dev/tmp/`:
  `e23-pixels-final2/`, `e-040-cache/`, `e-pause-exit/`.
- **E4. Overlap what stays on the blitter — closed after measurement.**
  - E4a. No interrupt-driven queue. The user approved closure if measurement
    supported keeping it out: final 060 reaches 25 fps with double buffering.
    Keep D1's disabled flight BLIT interrupts and native ordered blits.
  - E4b. The E2/E3 060 cycle profile measured 25 fps and 39.8% STOP idle;
    remaining map copy was 7.3%, scope 2.7%, tapes 2.5%, and the retained
    cockpit restore path 3.4%. These inclusive shares overlap and are not
    additive. Profile precedes the final panel-invalidation correction;
    final completed-swap measurements below confirm the target still holds.
    No 68000 rate or overlap work, per the C refocus.
- **E5. Expected outcome — measured and complete.**
  - E5a. The old mostly-geometry estimate is not established: chip copy,
    remaining blits and VBL pacing still matter. No claim of a universal
    mission-wide frame rate or a 1.5% geometry budget.
  - E5b. The two-field / 25 fps level is reached on the tested 50 MHz 030
    and 060 setups with double buffering. D4 stays closed.
  - E5c. Existing A3/A5 tools, normal startup and 500 PAL fields per final run:

    | Setup | Completed frames | FPS | World Hz | Input → next completed frame |
    |---|---:|---:|---:|---:|
    | a1200-fast (020) | 125 | 12.5 | 3.00 | 40–80 ms |
    | a1200-030 (50 MHz) | 250 | 25.0 | 3.00 | 20 ms |
    | a1200-060 (50 MHz) | 250 | 25.0 | 3.00 | 40 ms |

    These are short play windows. Delay samples depend on field phase and do
    not establish visible input response or scanout latency. Full-MMU 040
    CACHE smoke is correctness evidence, not a frame-rate measurement.
    Evidence: ignored `tmp/dev/tmp/e-final-fps{020,030,060}/`,
    `e-aprof-baseline060-current/`, `e-aprof-final060/`.

### F. Release

**Complete for 2.0b beta (21.10.2026).** F is closed for this beta on the
checks below. The full A3 matrix is not a beta gate. C's remaining acceptance
items (C-R1, C-R3–C-R5) and the deferred T-74 report stay open; this is not
full-release or full-mission sign-off.

- **F1. Options — complete.** CUSTOM1 is the default-off **Enhanced framerate**
  master, ignored below 68020. CUSTOM4 selects CPU (0, default) or native
  blitter (1) rendering, only within enhanced mode. CPU allocation failure
  retains the blitter. Double buffering remains; D4 stays cancelled.
- **F2. Versions — complete for the available releases.** `Gunship.slave`
  supports enhanced 0658; `GunshipNTSC.slave` supports enhanced 1489. The
  installer chooses by executable release, not video frequency. Both compile
  the same timing/rendering code with independently mapped code-hunk offsets.
  NTSC's shorter command decoder and longer weapons block retain their native
  layouts. Preparation validates native signatures and relocated operands.
  The 0658 address-map refactor was byte-identical before release metadata and
  the renderer option were added. Other recognized releases keep native timing;
  the unavailable German/alternate releases are explicitly untested in ReadMe.
- **F3. Version, ReadMe and installer — complete.** Version/date is
  **2.0b (21.10.2026)**. ReadMe and Install use the WHDLoad Install Template,
  retaining the original requirements, history, manual/icon credits, disk-file
  selection, support for the launcher in C:, and icon selection. The history
  entry lists user-visible changes since 1.2. `source/build.sh` builds both
  production slaves with the shared toolchain; diagnostic builds are not shipped.
- **F4. Final check — complete for the beta.**
  Existing blitter checks pass for PAL/NTSC title, menu and flight, including
  disabled-option behavior, delayed busy reads and register/flag preservation.
  Both release CPU gates ignore CUSTOM1 on 68000/010; no new 68000 rate or
  overload work was performed, per the refocus. The NTSC runtime's preparation
  and every live-hook signature pass. Both releases pass pause/exit, frozen
  paused state, no extra ticks after exit, and BLIT interrupt restoration.
  NTSC with CUSTOM1=0 also passes normal startup/takeoff without a timing
  arena: 15.12 fps and native 7.56 world Hz over 500 fields on 68060.
  Full-MMU 68040 CACHE startup/flight passed in FS-UAE. In that profile the CPU
  renderer is slower (6.12 fps) than the blitter (23.64); ReadMe recommends
  CUSTOM4=1 there. This is not a real-hardware performance result.

Current production-slave normal-startup measurements, one 500-field takeoff
window each, CPU renderer unless specified. Unseeded runs can select different
missions; these are not matched-state speedup comparisons or a full A3 matrix.

| Executable / video | CPU profile | fps | World Hz |
|---|---|---:|---:|
| 0658 / PAL | a1200-fast (020) | 13.9 | 3.00 |
| 0658 / PAL | 030, 50 MHz | 23.5 | 3.00 |
| 0658 / PAL | 060, 50 MHz | 22.0 | 3.00 |
| 1489 / NTSC | a1200-fast (020) | 10.44 | 3.00 |
| 1489 / NTSC | 060, 50 MHz | 30.0 | 3.00 |
| 1489 / NTSC, blitter | 060, 50 MHz | 18.24 | 3.00 |

Evidence is under ignored `tmp/dev/tmp/f-*`: normal-startup samples/results,
040 CACHE screenshots, the renderer comparison, and PAL/NTSC pause/exit results.
The completed E measurements remain applicable to the shared 0658 renderer.
Full A3-window/state-equality and full-mission acceptance are not claimed by
these short checks. The refocus's user mission checks remain C-R4/C-R5; native
68000 rate/full-mission expansion is excluded by the user's refocus decision.

### G. Optional: more of the world at field rate

Only after C is done, and only if C6's prediction of world objects shows visible errors at
25–50 fps. Move the free motion of the affected objects to field rate with C4's rules, while
their decisions, launches, hits and damage stay on the 3 Hz world tick:
- G1. Classify each quantity as a rate, an acceleration, a distance or a countdown, as Stunt Car
  Racer did in the playbook.
- G2. Audit each object type's motion code and its writers: AI, collisions, spawn and reset.
- G3. Validate behaviour in play, not only the arithmetic.

Raising the whole simulation rate, discrete logic included, is not planned. It would change
how often AI decisions and random draws happen, and so change how the game plays.
