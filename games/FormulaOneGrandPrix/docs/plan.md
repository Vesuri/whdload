# Plan: real-time game speed, up to 50 fps, faster on every machine

The goal, in the user's words: keep the world simulation and game logic rate stable (how
far a car moves in a second), allow frame rates up to 50, and make the movement and
rotation of the player and other objects smooth, with cars and physics behaving at
real-time speed whatever the frame rate. Improve performance on every system, especially
68020+ with fast RAM. This is a practical game optimisation, not an equivalence proof.

Steps have identifiers (`A1`, `C2`, ...). Take them in the order of [the critical path](#order-and-critical-path)
unless the user says otherwise; record each step's outcome where its *Output* says, and
keep [open work](open-work.md) pointing at the next step.

## What the measurements say

All from `docs/internals.md` (race main loop, memory and the chip bus, frame pacing,
game time). Times are emulated.

- **The game steps its world once per drawn frame,** about 1/8 s of game time per frame,
  and a frame pacer (hunk 0 `$127C`) busy-waits so that no frame is shorter than 6–7 PAL
  fields: never more than 8 fps. The in-game clock runs at 0.70× real time on the
  A500-equivalent, 0.93× on a stock A1200 and 1.02× on `a1200-fast`.
- **Drawing dominates; the simulation is cheap.** Per frame, drawing (`h2+280F6`) costs
  124 / 97 / 58 ms on the A500-equivalent / A1200 / `a1200-fast`, the per-car update
  (`h0+2AC14`) 39 / 26 / 10 ms. Everything else in the loop is at most about 3%.
- **On `a1200-fast` the game waits 22–43% of the time** in the pacer: faster code alone
  cannot raise its frame rate.
- **Hunk 2 (the renderer's code, 269 KB) is chip RAM.** 58% of the CPU's 14,742 chip-bus
  accesses per field are instruction fetches from it; the rest are mostly screen-buffer
  reads and writes. DMA reads only hunk 2's copper list (`h2+0000–0FFF`) and audio samples
  (`h2+18000–1DFFF`).
- **The 68020 instruction cache is off** under the supplied slave: WHDLoad's `CACHE`
  option alone cut the work per frame by 12%.
- **Display:** 4 lores planes, 320 × 200, `FMODE` 0, 52–56% of chip-bus slots free; the
  plane pointers are 4-byte but not 8-byte aligned.

**Projection (from the measured costs, not yet built):** a real-time 8 Hz world tick costs
8 × the per-car update per second, and the rest of the second goes to drawing.

| Machine | today | real-time tick, before optimisation |
|---|---|---|
| A500-equivalent | 5.8 fps at 0.70× | about 5.2–5.6 fps at 1.0× |
| A1200, no fast RAM | 7.2–7.7 fps at 0.93× | about 8 fps at 1.0× |
| `a1200-fast` | 8.0 fps at 1.02× | about 12–16 fps at 1.0× |
| 68030/50, 68040, 68060 | not measured (`A7`) | not measured |

## Design decisions

1. **Keep the native 1/8 s world step on every machine** and drive it from real time:
   an accumulator owes 8 ticks per 50 PAL fields (60 NTSC), exactly the pacer's long-run
   cadence, so the game speed on machines where the pacer already held 8 fps does not
   change. Slower machines run catch-up ticks without drawing. This is what makes game
   speed independent of frame rate; it touches no physics constant. (Wing Commander's
   10 Hz world accumulator, `docs/timing-design.md`; Revs' slow tick, `docs/faithfulness-seam.md`.)
2. **Smooth motion by presentation-only extrapolation** where frames are shorter than a
   tick (68020+ with fast RAM): snapshot the poses the renderer consumes at each tick's
   exit, draw `cur + (cur − prev) × α`, restore the authoritative values after drawing.
   The physics and AI never see predicted values. (Indianapolis 500 StingRay
   `tmp/dev/docs/slave.md`; Wing Commander `docs/internals.md` phases 10–11.) Input is
   still sampled once per tick; interpolation would add a tick of delay, which users of
   the sibling projects rejected even at 67 ms.
3. **Finer simulation steps only after an audit** (`F`), and only where the user asks:
   they are what Stunt Car Racer (`AGENTS.md` §Frame Rate Conversion) and Revs did, and
   the risk to F1GP's physics and AI is the reason they are optional here.
4. **Caches on** (the user's decision). Code that breaks with caches on is fixed (`B5`).
5. **Original behaviour one switch away:** every change behind a `CUSTOMn` bit with the
   original bytes untouched when off; the release exposes one player-facing option and
   gates per CPU and memory automatically (`G1`).

## Rules for every step

- Field counts need AmigaXDev's harness with `exact-fields` and `gapless-profile`
  (`quickrace` checks). Runs repeat exactly per machine and command sequence; anchor
  windows by screen or by game state, never by a field number copied from another
  machine or build.
- No performance claim without a matched measurement. Moving code shifts untouched code's
  cost by up to ±0.7% on the 68020 (AmigaXDev `docs/reference/m68k-optimisation.md` §1):
  compare against a control with the same layout. A larger slave can move the load
  address and change the race (Indianapolis 500): record hunk bases with every capture.
- Record facts in `docs/internals.md`, commands in `docs/development.md`, the next step in
  `docs/open-work.md`. Addresses as hunk offsets. Commit per coherent step.
- The gdb stub cannot write memory. Experiments that change the game go through the
  rebuilt slave (`B`), in a VERIFY or developer build. (Asking AmigaXDev for gdb memory
  writes would speed up `A3`/`A4`; it is optional.)

## Current validation scope: 68030 deferred

Current status: B1–B4 and A1/A2/A3/A5/A6 are complete. B5 has not passed: the
required 68040 non-MMU startup check was unsuccessful and work is stopped pending a
decision. A7 is incomplete; A8 has not started. See [open work](open-work.md) for the
next steps and [the startup evidence](internals.md#non-deferred-b5-check-68040-startup-also-unsuccessful)
for the limits of that finding.

At the user's direction, defer every 68030 cell in **B5, A7 and A8**, including
MMU and non-MMU configurations and both cache states. The shared startup wait and
diagnostic-tool findings are backlogged in AmigaXDev as TOOL1–TOOL3; do not address
those shared items in this session.

For this iteration, B5/A7/A8 acceptance covers the non-deferred machines. The remaining
scope includes 68000/68020 timing measurements and the required 68020/68040/68060 cache checks,
including 040/060 MMU functional tests. Report 68030 cells as **deferred**, never
measured or passed. Full 68030 qualification remains open for a later session;
this exception does not relax any gate for the remaining machines.

## A. Map the game (gdb, traces, static disassembly; no slave changes)

**A1 Time sources and race divergence.** Find every reader of time and randomness:
`$DFF004/6` (`VPOSR`/`VHPOSR`), every CIA timer and TOD register, the `$6C`/VBR level-3
vector, the field counter `h0+125E` and its copies `h0+125C`/`h0+1260`, the RNG routine(s)
and their seeds. Explain why the same Quick Race differs between machines (the
A500-equivalent never retires the player) and between runs with and without `CACHE`.
*Output:* internals "Time sources": each reader classified as simulation, presentation,
sound or hardware. *Gate:* the divergence is explained, or the timing input that causes
it is named.

**A2 The three main loops.** Identify the modes that run the loops at hunk 0 `$3C652`,
`$3C8F6` (the race) and `$3CC40` (practice, qualifying, replay, attract?) by reaching each
mode (extend `quickrace`'s menu route) and counting call-site executions in a profile.
List every caller of the pacer and of `h2+280F6`. *Output:* internals "Race main loop".

**A3 Simulation versus presentation, call by call.** For every call in each live loop,
find what it writes. Tool: a new `tools/state_diff.py` that breaks at a call site and at
its return, dumps hunk 1, hunk 0's and hunk 2's data, and the non-screen part of hunk 3,
and classifies the changed bytes per call over 50 frames. Pay special attention to
`h2+280F6`: anything the drawing writes that the simulation later reads (camera and view
selection, "Viewing" cuts, timers, RNG draws, animation phases such as the marshal and
tow truck, sound triggers, visibility results). Revs' physics read the painted screen
(grip from pixels): check whether F1GP's simulation reads anything the renderer produces.
*Output:* a table in internals of each call's class and its writes; the list of drawing
side effects that must run once per tick. *Gate:* every write by the drawing is
classified.

**A4 State map.** The car record layout (position, heading, pitch, roll, speed, track
segment pointer and fraction, lateral offset, wheel and steering angles), the camera
records (cockpit, TV cameras, chase, onboard other cars, replay), the view and
camera-source variables, and which of those fields each view's renderer reads. Start from
`h0+2AC14`'s record walk (records reached through an offset list, each pointing at its
track segment) and the renderer's absolute references into hunk 1. *Output:* internals
"State map", with hunk-1 offsets.

**A5 Display publication.** How the back buffer is chosen, where and when the buffers
swap (copper list at `h2+0000`, main loop or interrupt), whether the swap waits for a
vertical blank, and what happens if two frames finish within one field. *Output:*
internals; a publication rule safe at 50 fps (draw only into the buffer not on screen,
swap at a vertical blank, wait while a swap is pending; AmigaXDev
`simulation-and-presentation.md` §LoadView).

**A6 Interrupts and input.** The level-3 handler at `h0+2CC38` (field counter increment
at `h0+2CC3C`), the KickEmu interrupt chain (about 1.2% of cycles), where the keyboard,
joystick and mouse are sampled (per field or per frame), and engine sound: the per-frame increment calculation at `h0+36288`, which scales
by `h0+125C`, and its per-field application in the interrupt. *Output:* internals.

**A7 Machine matrix.** Profile green, tow and follow (`RACE_LEADS=0,0,0` on machines
without calibrated leads) on the A500-equivalent, `a1200`, `a1200-fast`, a cycle-exact
68030/50, `68040-NOMMU`/25 and `68060-NOMMU`/50 (AmigaXDev playbook §8), each with and
without `CACHE`, and run `race_clock.py` on each. Fix the 68030 run that timed out before
(longer deadlines). *Output:* internals tables: fps, drawing ms, tick ms, chip slots,
game clock ratio per machine. *Gate:* every cell measured or its failure explained.

**A8 Renderer ceiling** (after `B4`). Developer-build options: no pacer wait (the
`bcs.w` at hunk 0 `$1288` falls through), no polygon fill (an `rts` at the filler's
entry, same layout), and an instant-blitter run. Measure the maximum frame rate per
machine with the native coupling (the game runs fast: a measurement, never a mode).
*Output:* internals; the ceiling bounds what `D` can show before `E`.

## B. Rebuild the slave (no source is available)

**B1 Read Codetapper's slave.** Turn `tmp/re/slave.dis` into reassemblable source.
Separate KickEmu's kick13 code from Codetapper's loader. Decode the three
`resload_PatchSeg` lists (slave `$2A6`, `$2DC`, `$312`, one per `f1gp` size) and the
driver-names patch (`$3D6`): offset, original and new bytes, purpose. *Output:* internals
"Slave".

**B2 New slave source.** `whdload/` with the playbook §10 build (vasm, shared WHDLoad
kit, `slv_Version` 17, KickEmu kick13), reproducing the loader: assigns, `frontend`
unless `CUSTOM1` or fire, `LoadSeg` of `f1gp`, the patch list for each known size, driver
names, quit. Pin the toolchain inputs in `manifest/`; built slaves stay in `tmp/`.

**B3 Establish the modern-KickEmu baseline.** Retain the shared KickEmu fixes rather
than reproduce the 2002 implementation's allocation and startup timing. Verify the
supplied game's loader patches and restored names in captured memory, navigate the
Quick Race menus, and exercise F10 quit. Capture green, tow and follow for 500 fields
each, twice from fresh deterministic boots with identical screen-anchored commands.
Record slave and emulator hashes, game input pins and actual hunk bases. Keep the
original-slave comparisons as reference evidence and explain observed differences;
matching its timing-dependent random race is no longer the acceptance criterion.
*Output:* internals baseline results and development commands. *Gate:* all three paired
windows have identical routes, anchors, hunk layout and every screenshot digest;
loader checks and clean quit pass. This establishes repeatability of the modern build,
not equivalence to the original. Other game-file variants remain unverified until supplied.

**B4 Gating and checks.** `CUSTOMn` bits in `slv_config`; a checker that, with every bit
off, confirms the original bytes of every hooked range, reading the ranges from comments
beside each hook (Legends of Valour's `PERF_RANGE` pattern); developer and VERIFY build
targets.

**B5 Caches on.** Enable the instruction cache, and the data cache where the CPU has
one, through `resload_SetCPU` or KickEmu's `CACHE`; log `CACR` in VERIFY. Run menus and a
whole race with caches on, on the 68020, 68030 (with and without WHDLoad's `MMU`), and
68040/68060 (`NOMMU` and with MMU). Look for code writing code (none seen in the race
windows: hunk 2's written words are data after `RTS`), CPU reads of blitter results
without a blitter wait, and buffers written by the CPU and read by DMA. Fix every failure
in the game code (cache flush after writing code, blitter waits) instead of turning
caches off. *Gate:* a whole race and the menus on every CPU with caches on; the gain
recorded per CPU (68020: −12% work measured).

## C. Real-time world clock (every machine)

**C1 Clock.** Owe 8 ticks per 50 fields on PAL and per 60 on NTSC (detect the field rate
as the game does, with its chip word compared with 60). Take fields from the game's own
interrupt counter or a slave-owned one in the same handler. Write the design in internals
"Game time".

**C2 Loop.** Replace the pacer call in each live loop (`A2`) with: add the elapsed fields;
run due ticks (the simulation calls of `A3`, in native order) up to 4 per batch; drop debt
beyond 1 s (count it in VERIFY); draw once (the presentation calls); publish by the `A5`
rule; never more than one picture per field. Keep `h0+125C`'s meaning for the engine
sound: fields per tick. Run every drawing side effect the simulation needs (`A3`) once per
tick, not once per picture.

**C3 Modal boundaries.** Start lights, pit stops, retirement and tow, replays, pause,
menus, the end of the race, loading, the results screens. For each, the world clock
either runs as the native game would or rebases without backlog; scripted sequences that
count frames become real-time automatically if they run in the tick.

**C4 Input.** Player input is sampled where the native game samples it, per tick; one-shot
keys (views, pause) act exactly once; nothing is lost while catch-up ticks run.

**C5 Acceptance.** (a) `race_clock.py` on every machine of `A7`: game clock ÷ real time
1.00 ± 1% wherever the ticks fit the CPU. (b) Tick-aligned state: car records at each
completed tick identical between normal, deliberately slowed (VERIFY delay) and
one-field drawing, given the `A1` timing inputs held equal; classify any difference.
(c) A whole race, a pit stop, a retirement and a replay played through. *Gate:* (a) and
(c) pass; (b) passes or every difference is classified.

**C6 Slow machines.** Measure the A500-equivalent and A1200 after `C2` against the
projection (about 5.2–5.6 and 8 fps at 1.0×), including the heaviest scene (the tow
window). If the A500 cannot sustain real time in some scenes, the debt cap applies and the
user decides whether the 68000 defaults to the original frame-locked behaviour.

## D. Smooth presentation (68020+ with fast RAM, when pictures are shorter than a tick)

**D1 Snapshot.** At each tick's exit, copy the fields each view's renderer reads (`A4`)
into `prev` and `cur`, with the field number.

**D2 α.** (fields since the tick's exit + fields until the picture is shown) ÷ fields per
tick, in Q14, clamped. "Until shown" comes from the `A5` publication rule and the last
picture's drawing time (Wing Commander's display-field horizon). When pictures are longer
than a tick, show the latest state and skip prediction (Red Baron).

**D3 Stage and restore.** Write predicted values into the renderer's inputs (or a
renderer-only copy), draw, restore the authoritative values exactly before any
simulation code runs. VERIFY checks the restore on every picture.

**D4 Camera.** Position and heading, pitch, roll: `cur + (cur − prev) × α`; angles by the
shortest arc, track position across the lap wrap; snap (α = 0) at view changes, TV-camera
cuts and the first tick after a rebase.

**D5 Cars.** The same formula first. Then check the per-car update's order: if a car's
rates are set before it moves, derive the exact next pose with the native arithmetic
(Indianapolis 500's opponents: largest heading jumps 133 → 33). Snap at teleports (pit
lane, retirement removal, crash resets) and when a car enters view.

**D6 Everything else that moves.** Wheels and steering, the marshal and tow truck,
flags, smoke and debris, mirrors, the rev counter and the other instruments: per item,
extrapolate, hold at the tick, or animate on a presentation clock. Mirrors use the same
staged poses.

**D7 Every view.** Cockpit, TV cameras, chase, onboard other cars, replays, the attract
mode if there is one: each consumes its own records (Indianapolis 500's replays froze
because only the car records were snapshotted).

**D8 Prediction error.** For every tick, compare the prediction at α = 1 with the next
actual pose: p50 and p95 per quantity, worst cases at braking, steering reversal,
collisions. Set snap thresholds from them.

**D9 Smoothness.** At 50 fps on the 68060: per-field screenshots show the camera and cars
moving every picture, never backwards; a frame-time histogram per window.

**D10 Play-test.** The user judges the feel. Input still takes effect at the next tick.

## E. Performance (each change gated by measurement on every CPU)

**E1 Caches:** `B5`.

**E2 Hunk 2's code in fast RAM** (68020+ with real fast RAM). Copy hunk 2's code ranges
(static disassembly plus trace coverage) into a fast block. Redirect absolute references
to code inside the copied ranges (from hunk 0's and hunk 2's relocations: `JSR`, `JMP`,
`LEA` of code, jump tables) to the copy. Leave references to data pointing at chip RAM, so
the variables between routines, the copper list and the samples stay authoritative where
they are. Find PC-relative data reads in the copied code: they would read the copy's
stale bytes. Flush caches after copying. Expected: the 8,532 chip instruction fetches per
field (follow window), at least 4 CPU cycles each, at least 12% of all cycles before wait
states, become fast-RAM fetches; Powerdrome gained most from exactly this. *Gate:* the
same pictures at the same ticks with the copy on and off; the gain per CPU.

**E3 Draw in fast RAM, copy to chip.** A fast back buffer; the blitter's operations on
the back buffer (1.3–2.2% of slots) replaced by CPU fills in fast RAM; a `MOVEM` copy of
the 32,000-byte picture into the chip back buffer just before publication. Powerdrome's
bitmap alone gained nothing on the 68020, so measure after `E2` and keep it only where it
wins. *Gate:* pixel twin of the picture; gain per CPU.

**E4 Hot routines.** Re-profile after `E1`–`E3`, then work on the top entries. Before
`E2` they are (follow window, inclusive of callees): `h2+29C16` (16.4%), `h0+1F388`
(16.1%, called from about 28 sites in `h2+266CE–27CB8`), `h0+1EABA` (8.0%, from
`h2+26028–264B2`), `h0+147C` (5.0%), and the self-time leaders `h0+2AC14`'s loop,
`h2+232C4`, `h2+23320`, `h2+245B0`. Identify each (fills, spans, transforms),
look for work not done first (AmigaXDev `m68k-optimisation.md` §10), then 68020 forms
(scaled index, bit-field instructions, 32-bit multiply, inner loops inside the 256-byte
instruction cache). Twin every replacement against the original (Indianapolis 500
`pixel_verify.s`); keep the original on any CPU where it is not faster.

**E5 AGA 32-bit fetch.** On AGA only, `FMODE` 1 or 2 with `DDFSTOP` adjusted; write
`FMODE` 0 on OCS/ECS. The plane pointers already meet the 4-byte alignment; 64-bit
(`FMODE` 3) would mean moving the screen buffers to 8-byte alignment and is worth it only
if 32-bit gains. Check every screen's picture. Expect little: half the bus is free, and
after `E2`/`E3` the CPU's chip traffic is mostly the copy.

**E6 Chip data the CPU reads.** About 800 reads per field from hunk 2's tables and 670
from `$50000–$53FFF` (follow). Move CPU-only hot tables to fast RAM only if `E4`'s profile
shows them significant.

**E7 The 68000.** Chip-only machines gain only from executing less. Re-profile the
A500-equivalent after `C`, apply `E4`'s findings in 68000 forms, twin, and keep each only
where it wins.

**E8 Interrupt overhead.** The KickEmu interrupt chain (about 1.2%): leave unless cheap.

## F. Finer simulation (optional; only on the user's request after `D10`)

**F1 Per-field steering preview.** Preview the native player motion every field from the
current input and spread it over the tick (Gunship `TIMING_DESIGN.md`), so steering
shows within a field. Needs a side-effect-free preview of the player physics.

**F2 Finer world step.** A units-and-writers audit of the car physics and AI: integrators,
damping, thresholds, timers, RNG draws, per-quantity scaling (AmigaXDev
`fixed-time-simulation.md` §Raising the update rate; Stunt Car Racer; Revs'
`tools/sim_equiv.py`). Large and risky; not part of the main path.

## G. Release

**G1 Options.** One player-facing toggle for the enhanced mode, with automatic gating:
68000 and chip-only machines get `C` (and `E7`), 68020+ with fast RAM get `C`, `D` and
`E`. Whether it defaults on is the user's decision. A developer build keeps individual
`CUSTOMn` bits.

**G2 Regression routes.** Quick Race, practice, qualifying, a full race weekend, a pit
stop, a retirement, a replay, every view, menus and options, a second race (tables and
state reset), NTSC; every CPU, caches on.

**G3 Final numbers.** The `A7` matrix and race-clock ratios after all changes, in
internals; the ReadMe's requirements (memory, CPU) and options.

**G4 Release archive** (AmigaXDev playbook §13).

## Order and critical path

1. `A1`, `A2`, `A3`, `A5`, `A6` (understanding) and `B1`–`B4` (slave) in parallel; `A7`
   any time.
2. `B5` (caches) and `A8` (ceiling) as soon as `B4` exists.
3. `C1`–`C6`: real-time game speed on every machine.
4. `A4`, then `D1`–`D10`: smooth pictures on 68020+.
5. `E2`, `E3`, `E4` (they can start after `B4`, independently of `C` and `D`), then `E5`–`E8`.
6. `F` only if asked; `G` last.
