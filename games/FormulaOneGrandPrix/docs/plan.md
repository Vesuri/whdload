# Plan: real-time game speed, up to 50 fps, faster on every machine

The goal, in the user's words: keep the world simulation and game logic rate stable (how
far a car moves in a second), allow frame rates up to 50, and make the movement and
rotation of the player and other objects smooth, with cars and physics behaving at
real-time speed whatever the frame rate. Improve performance on every system, especially
68020+ with fast RAM. This is a practical game optimisation, not an equivalence proof.
Game modifications belong to F1GP-Ed, which edits the `f1gp` file; the slave must run any
F1GP-Ed-edited file with these enhancements (user decision; `F`).

Steps have identifiers (`A1`, `C2`, ...). Take them in the order of [the critical path](#order-and-critical-path)
unless the user says otherwise; record each step's outcome where its *Output* says, and
keep [open work](open-work.md) pointing at the next step.

## What the measurements say

The following original-baseline findings are from `docs/internals.md` (race main loop,
memory and the chip bus, frame pacing, game time). Times are emulated. The current
cache matrix and ceiling results are recorded in its A7/A8 sections; those do not
replace the original baseline or prove the projected implementation below.

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
| 68030/50, 68040, 68060 | see A7; 040/060 CPU profiles unavailable | not implemented |

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
   the sibling projects rejected even at 67 ms. The D10 play-test found extrapolation's
   steering jumps worse, and the user chose interpolation, shown a tick plus the measured
   lead late (user decision; D10).
3. **Finer simulation steps only after an audit** (`H`), and only where the user asks:
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

## Current validation scope

Current status: B1–B4 and A1–A6 are complete. A4 maps the native car/camera/view inputs
and validates camera publication in 250 retained A3 snapshots (see internals State map).
A7 meets its gate with 24 CPU-timing cells measured and 12 unavailable 040/060 cells explained; all field/DMA
and whole-race captures repeat exactly. B5's functional races pass, but its 040/060
work gains remain unavailable. A8 has accepted A500/A1200/020/030 ceilings; a developer-only startup notification
control fixes the 030 layout mismatch. Its 040/060 CPU timings remain unavailable. B5 and A8
pass for the current scope below; their 040/060 timing items are deferred. See [open work](open-work.md).
C1, the developer-only C2 loop and C3 modal boundaries are complete.
C2's selected-state/picture, publication, sound and disabled-feature checks are in internals;
C3's modal ownership and rebase checks are recorded there too. C4's held-view and joystick
probes pass, but a short press released between scans is lost in the native state table.
C4 is complete: one-shot presses are buffered until a native scan has seen them (user
decision), and every view key, pause, double tap and replay tap act exactly once. C5 is complete: the tick rate is 7.987 per emulated second
with no drops on the 030 and A1200 (the A500-equivalent is overloaded, C6's question), the
race clock keeps its native ratio, normal and slowed drawing give identical state at every
tick, and race, retirement, replay and the accepted pit coverage pass. C6 is complete: the
A1200 holds real time, but an undrawn tick costs the A500-equivalent 7.2 fields, so the
68000 keeps the original frame-locked pacer by default (user decision). D1–D9
are complete (presentation snapshots, α, staging with exact restore, camera and car
prediction, the remaining moving items, every view); D8 measured the prediction error
and kept the snap thresholds; D9 showed every picture moving forward on the 030. D10 is
complete: the horizon glitch its play-test found is fixed, pictures interpolate instead of
extrapolating, and the user accepted the feel (user decision).

**Target machines (user decision).** The 68030/50 with Fast RAM (`a1200-030` non-MMU,
caches on) is the primary target. Keep the number of configurations as small as possible:
from now on, run new checks on that machine only, adding the A500-equivalent and the
A1200 only where a step is about slow machines (C6, the debt cap) and PAL only unless
the step is about NTSC. Don't repeat the 020, MMU or cache-off arms; their existing
evidence stands. 68040/68060 work is
deferred until everything else is done, if it is done at all: their existing functional
passes (menus, whole races, MMU pairs) stand, but no step waits for 040/060 timing,
gains or ceilings. FS-UAE's cycle-exact 040/060 cores charge no time for instruction
execution or Fast RAM, so their emulated timing is an instruction count and cache gains
can't be measured there; AmigaXDev's aprof emulator can count their instructions, and
timing claims need a real accelerator. All remaining measurements use the exact-repeat method.

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

**C1 Clock.** Owe 8 ticks per 50 fields on PAL and per 60 on NTSC. Detect the display
family from a complete video-beam sweep at epoch entry; C2 testing found that the
native chip word stays at 50 under NTSC, and the user approved beam detection. Take fields from the game's own
interrupt counter or a slave-owned one in the same handler. Write the design in internals
"Game time". Use only whole updates and integer VBL accounting; no new CIA timer
or fractional simulation steps. C1 is a design output; hook installation belongs to C2.

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

**C5 Acceptance.** (a) On the 68030/50, the A500-equivalent and the A1200 (PAL): world
ticks ÷ real time 8.00 per second ± 1% wherever the ticks fit the CPU. The displayed
race clock is measured separately with `race_clock.py` and keeps its native
2111/16384 s per tick, 1.031× real time at 8 ticks per second (user decision). (b) Tick-aligned state: car records at each
completed tick identical between normal, deliberately slowed (VERIFY delay) and
one-field drawing, given the `A1` timing inputs held equal; classify any difference.
All three run on the 68030; one-field drawing uses the same machine with FS-UAE's fastest
non-cycle-exact CPU, because a faster cycle-exact clock barely shortens its pictures (user
decision). (c) A whole race, a pit stop, a retirement and a replay played through. For
the pit stop, the practice pit-box release and C3's in-pit accelerated time are accepted
as the coverage; a service after driving into the box is not exercised, because no
unattended car pits (user decision). *Gate:* (a) and
(c) pass; (b) passes or every difference is classified.

**C6 Slow machines.** Measure the A500-equivalent and A1200 after `C2` against the
projection (about 5.2–5.6 and 8 fps at 1.0×), including the heaviest scene (the tow
window). If the A500 cannot sustain real time in some scenes, the debt cap applies and the
user decides whether the 68000 defaults to the original frame-locked behaviour. *Result:* it does (user decision); the clock is installed only above the 68000,
or with the developer `CUSTOM2` bit 2.

## D. Smooth presentation (68020+ with fast RAM, when pictures are shorter than a tick)

**D1 Snapshot.** At each tick's exit, copy the fields each view's renderer reads (`A4`)
into `prev` and `cur`, with the field number.
*Result:* complete behind `CUSTOM2` bit 3 ([internals](internals.md#d1-presentation-snapshots--complete)):
2232-byte cur/prev buffers, checked against game memory at every tick of a whole 030 race,
read-only for the game, 0.24 ms per tick.

**D2 α.** (fields since the tick's exit + fields until the picture is shown) ÷ fields per
tick, in Q14, clamped. "Until shown" comes from the `A5` publication rule and the last
picture's drawing time (Wing Commander's display-field horizon). When pictures are longer
than a tick, show the latest state and skip prediction (Red Baron).
*Result:* complete ([internals](internals.md#d2-presentation-phase-α--complete)). Phase
from the clock's credit (fields since the tick fell due), lead measured per picture kind,
α 0 when pictures (lead or period) are longer than two ticks (one tick before D9), clamped to two ticks because
pictures drawn between ticks are displayed after the next tick is due.

**D3 Stage and restore.** Write predicted values into the renderer's inputs (or a
renderer-only copy), draw, restore the authoritative values exactly before any
simulation code runs. VERIFY checks the restore on every picture.
*Result:* complete ([internals](internals.md#d3-stage-and-restore--complete)). A 1080-byte
pose subset of the D1 layout is staged into the game around each picture's draw and
restored right after it; VERIFY checks every restore against a snapshot. A VERIFY probe
that draws the previous tick leaves the whole 030 race identical to the option off.
D4/D5 supply the predicted values.

**D4 Camera.** Position and heading, pitch, roll: `cur + (cur − prev) × α`; angles by the
shortest arc, track position across the lap wrap; snap (α = 0) at view changes, TV-camera
cuts and the first tick after a rebase.
*Result:* complete ([internals](internals.md#d4-camera-prediction--complete)). The
published camera is extrapolated, the road anchor comes from the game's own segment search,
and coefficients, horizon and viewport are recomputed natively. Over a whole 030 race the
model rebuilds every prediction exactly, the p95 camera position error falls from 490k to
30k world units, and the race is unchanged.

**D5 Cars.** The same formula first. Then check the per-car update's order: if a car's
rates are set before it moves, derive the exact next pose with the native arithmetic
(Indianapolis 500's opponents: largest heading jumps 133 → 33). Snap at teleports (pit
lane, retirement removal, crash resets) and when a car enters view.
*Result:* complete ([internals](internals.md#d5-car-prediction--complete)). Track-driven
cars advance along their segments by fraction with the native stepping, explicit cars in
world X/Z with the game's segment search; a car is held at pit transitions, flag, status
or jump changes and on the grid. Every record advances every tick, so entering view needs
no snap. No exact next pose exists: the advance uses a speed set during the next tick.
Over a whole 030 race the model rebuilds every car exactly, the p95 car position error
falls from 494k to 25k world units, and the race is unchanged.

**D6 Everything else that moves.** Wheels and steering, the marshal and tow truck,
flags, smoke and debris, mirrors, the rev counter and the other instruments: per item,
extrapolate, hold at the tick, or animate on a presentation clock. Mirrors use the same
staged poses.
*Result:* complete ([internals](internals.md#d6-everything-else-that-moves--complete)).
Steering is held: it follows input and reverses abruptly, and over a whole 030 race
holding leaves fewer wrong wheel images than extrapolating. The tow truck, smoke and
debris are drawn at offsets from the predicted car, and the rear view and pit-lane
overlay from the staged camera. Flags, start lights, pit phases, shake, instruments and
car flags are tick states and stay at the tick; none needs a presentation clock. One
gap was fixed: the covered-road (no-sky) flag now follows the predicted anchor.

**D7 Every view.** Cockpit, TV cameras, chase, onboard other cars, replays, the attract
mode if there is one: each consumes its own records (Indianapolis 500's replays froze
because only the car records were snapshotted).
*Result:* complete ([internals](internals.md#d7-every-view--complete)). The cockpit,
onboard and replay views draw from the staged records; there is no attract mode (A2). In
the chase and TV views the camera is now placed and aimed natively from the predicted
followed car, so camera and car agree. Pit stops swap track ranges, which the check now
captures per picture. A whole 030 race through every view and a replay is rebuilt exactly
and identical to the option off at all 3246 ticks.

**D8 Prediction error.** For every tick, compare the prediction at α = 1 with the next
actual pose: p50 and p95 per quantity, worst cases at braking, steering reversal,
collisions. Set snap thresholds from them.
*Result:* complete ([internals](internals.md#d8-prediction-error--complete)). Over the
D7 race at α = 1:
- the camera's p95 position error is 21,504 against 446,880 for holding the tick;
- the cars' is 22,784 against 430,080;
- braking barely raises it; steering reversals make yaw extrapolation worse than holding;
- collisions change the pose flag or status, so the car is already held.

The thresholds stay:
- the $100000 jump, twice the largest normal movement, while the error does not grow with movement;
- the two-tick α clamp, where prediction is still 14 times closer than holding;
- three segments per tick.

The largest car errors are D5's holds at the pit branch and join while pit stops are on.

**D9 Smoothness.** At 50 fps on the 68060: per-field screenshots show the camera and cars
moving every picture, never backwards; a frame-time histogram per window.
*Result:* complete on the 68030/50 ([internals](internals.md#d9-smoothness--complete));
the 68060 run is deferred with the other 040/060 work. Two causes of backward motion
were fixed: D5 held a car whose predicted step reached a pit change (it now stops at the
end of its segment), and D2 gave α 0 to a single picture just over a tick (now only
beyond two ticks). Over a whole race:
- the camera never steps back and stalls in 6 of 4579 moving picture pairs (2127 showing
  the tick);
- cars step back 51 times in 139,607, at most 14,734 world units, mostly off the grid;
- steps are even, p5–p95 0.76–1.30 of the ideal against 0–2.1;
- on screen, 98–100% of predicted pictures change the view, against once a tick
  without prediction;
- frame times are 3–4 fields in the cockpit and chase views and 5 in TV.

**D10 Play-test.** The user judges the feel. Input still takes effect at the next tick.
The first 040 play-test found the horizon drawn over the 3D on repeats (fixed in C2) and
steering jumps from extrapolation. Pictures now interpolate between the last two ticks,
each shown a tick plus the longer measured lead late so that the steps stay even (user
decision). In the second 040 play-test the user found steering smooth, without jumps, and
the chase, TV and onboard views, replay cuts and pit entry fine; the pit-stop sprites are
now interpolated too. *Complete:* the user accepted the feel, the extra lag included.

## E. Performance (each change gated by measurement on every CPU)

**E1 Caches:** `B5`. *Complete for the current scope:* B5's gate, plus the gain with the
C2 loop and interpolation on the 030 — 13–14% more pictures over a whole race with caches
on. The slave keeps them opt-in (all bits zero stay original); the release turns them on
through its icon (`G1`).

**E2 Hunk 2's code in fast RAM** (68020+ with real fast RAM). Copy hunk 2's code ranges
(static disassembly plus trace coverage) into a fast block. Redirect absolute references
to code inside the copied ranges (from hunk 0's and hunk 2's relocations: `JSR`, `JMP`,
`LEA` of code, jump tables) to the copy. Leave references to data pointing at chip RAM, so
the variables between routines, the copper list and the samples stay authoritative where
they are. Find PC-relative data reads in the copied code: they would read the copy's
stale bytes. Flush caches after copying. Expected: the 8,532 chip instruction fetches per
field (follow window), at least 4 CPU cycles each, at least 12% of all cycles before wait
states, become fast-RAM fetches; Powerdrome gained most from exactly this. *Gate:* the
same pictures at the same ticks with the copy on and off; the gain per CPU. *Complete for
the current scope:* the safe closures of 244 of 256 entries (h2+$1D820–$2A640) run from a
copy switched on at the first live epoch; the race is identical and every picture rebuilt,
and the 030 draws 31–32% more pictures. Hunk 2 can't move whole: DMA reads its copper list
and samples.

**E3 Draw in fast RAM, copy to chip.** A fast back buffer; the blitter's operations on
the back buffer (1.3–2.2% of slots) replaced by CPU fills in fast RAM; a `MOVEM` copy of
the 32,000-byte picture into the chip back buffer just before publication. Powerdrome's
bitmap alone gained nothing on the 68020, so measure after `E2` and keep it only where it
wins. *Gate:* pixel twin of the picture; gain per CPU. *Complete for the current scope:*
behind a developer option the picture is drawn in a persistent fast buffer, its fills and
queued blits run on the CPU, and publication copies it into the free chip back buffer, so
acquire no longer waits for the display. Every fill and queued blit of a race matches the
blitter byte for byte, the race is identical, and with E2 the 030 draws 2.05–2.07 times as
many pictures. The copy is now its main cost.

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
if 32-bit gains. Check every screen's picture. The plan expected little (half the bus is
free, and after `E2`/`E3` the CPU's chip traffic is mostly the copy), but `E4` found the
polygon filler bound by chip data, so measure. f1gp.library (F1GP-Ed's companion) set
`FMODE` `$000F` (64-bit bitplane and sprite fetch) with its own display-window and
data-fetch values; how it met the 8-byte alignment is not established.

**E6 Chip data the CPU reads.** About 800 reads per field from hunk 2's tables and 670
from `$50000–$53FFF` (follow). Move CPU-only hot tables to fast RAM only if `E4`'s profile
shows them significant.

**E7 The 68000.** Chip-only machines gain only from executing less. Re-profile the
A500-equivalent after `C`, apply `E4`'s findings in 68000 forms, twin, and keep each only
where it wins.

**E8 Interrupt overhead.** The KickEmu interrupt chain (about 1.2%): leave unless cheap.

## F. F1GP-Ed compatibility (after `E`)

F1GP-Ed 3.44 (Oliver Roberts; closed source, donationware, files may be redistributed
only unchanged) is how Amiga players modify F1GP. It has three kinds of change: settings
saved into the `f1gp` file (the size stays 582,992 bytes), memory patches that run from
F1GP-Ed's own process beside the game, and f1gp.library's in-memory patches. Under
WHDLoad only the first kind applies: the operating system is gone, so nothing runs beside
the game. F makes the slave and every file edit live together; the enhancements stay in
the slave, because they need WHDLoad's caches, fast memory and the hardware.

**F1 Write map.** Pin `F1GP-Ed.lha` and the f1gp.library developer archive in
`manifest/`. Run F1GP-Ed under FS-UAE with Workbench on copies of `f1gp` in `tmp/` and
diff the file after each setting (one at a time, at their extremes) and after each
supplied datafile; saving to the file needs the GUI, `SAVETOMEM` plus a memory dump
covers the memory path. *Output:* in internals, each setting's hunk ranges, data or code,
and its values; no game bytes.

**F2 Collisions.** Compare the write map with every `PL_*` site, `E2`'s copied ranges,
the `C`/`D` hooks and the state `C`/`D` read. Classify each overlap as harmless, needing
handling, or incompatible.

**F3 Frame rate and timing.** F1GP-Ed's frame rate sets the pacer minimum and the
simulation step (`h0+$34364`; [evidence](internals.md#native-time-step-and-f1gp-eds-frame-rate-f3-evidence)):
n fields per frame, a step of n × 1350/65536 s on PAL. The user wants it supported: the
clock delivers 65536 ÷ step updates a second instead of 8, and D interpolates them to
the display rate (up to 50 fps). Confirm which step words F1GP-Ed writes (F1), make C's
schedule, D's α and thresholds and the sound denominator follow the step, and run
`C5`, `D8` and `D9` at each setting. The PAL/NTSC timing setting is traced the same way.

**F4 Edited-file inputs.** Build edited `f1gp` files reproducibly from pinned datafiles
and settings, plus one edited cockpit and one replaced backdrop, and pin their hashes.
Run the `B4` gate, `C5`, `D8`/`D9` and whole races on the 030 and A1200 against them.

**F5 Fixes.** Keep size-based version detection. Make each colliding patch robust:
verify the original bytes before patching, or turn the affected feature off for that
file. Document the slave's baseline overrides (requester filter button, default save
directory, 1991 names).

**F6 Memory-patch features** (optional; user decision). Reimplement chosen F1GP-Ed memory
patches (GPPatch, PatchF1GP, per-circuit factors, f1gp.library fixes) as slave options,
configured from an F1GP-Ed datafile; F1GP-Ed's own code is not copied.

## G. Release

**G1 Options.** One player-facing toggle for the enhanced mode, with automatic gating:
68000 and chip-only machines get `C` (and `E7`), 68020+ with fast RAM get `C`, `D` and
`E`. Whether it defaults on is the user's decision. A developer build keeps individual
`CUSTOMn` bits.

**G2 Regression routes.** Quick Race, practice, qualifying, a full race weekend, a pit
stop, a retirement, a replay, every view, menus and options, a second race (tables and
state reset), NTSC; every CPU, caches on; the stock file and `F4`'s edited files.

**G3 Final numbers.** The `A7` matrix and race-clock ratios after all changes, in
internals; the ReadMe's requirements (memory, CPU) and options, and which F1GP-Ed
settings the slave honours, overrides or rejects (`F`).

**G4 Release archive** (AmigaXDev playbook §13).

## H. Finer simulation (optional; only on the user's request)

The game's own variable step (`F3`) already gives a finer world step that F1GP-Ed players
have used for decades; with `F3` the slave can offer it without F1GP-Ed. Its known side
effects (computer cars slower, spins in long races at 20–25 fps) are what to measure
before H2's audit is considered.

**H1 Per-field steering preview.** Preview the native player motion every field from the
current input and spread it over the tick (Gunship `TIMING_DESIGN.md`), so steering
shows within a field. Needs a side-effect-free preview of the player physics.

**H2 Finer world step.** A units-and-writers audit of the car physics and AI: integrators,
damping, thresholds, timers, RNG draws, per-quantity scaling (AmigaXDev
`fixed-time-simulation.md` §Raising the update rate; Stunt Car Racer; Revs'
`tools/sim_equiv.py`). Large and risky; not part of the main path.

## Order and critical path

1. `A1`, `A2`, `A3`, `A5`, `A6` (understanding) and `B1`–`B4` (slave) in parallel; `A7`
   any time.
2. `B5` (caches) and `A8` (ceiling) as soon as `B4` exists.
3. `C1`–`C6`: real-time game speed on every machine.
4. `A4`, then `D1`–`D10`: smooth pictures on 68020+.
5. `E2`, `E3`, `E4` (they can start after `B4`, independently of `C` and `D`), then `E5`–`E8`.
6. `F` after `E`; `G` after `F`; `H` only if asked.
