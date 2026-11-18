# Open work

Set up 18.11.2026: `src/` is JOTD's v3.1 source with three changes that make vasm assemble
it, equivalent to the shipped slaves apart from the newer KickEmu (`development.md`,
"Build"). All three variants boot to the duty roster. The AGA flight is profiled
(`development.md`, "Profiling in flight"); the target is 50 fps in flight on the a1200-030
(soft). P1-P4, P5a/P5c and P6-P8 of the plan are done (P5b measured, not done): the VERIFY
build pins the mission, the release slaves keep the flight's stack and its model data in
fast RAM and turn the instruction cache on, `CUSTOM2=1` ("Enhanced framerate") lifts the
frame cap with the simulation kept at its rate, and the CPU fills the polygons (68030 or
later) and the one-colour rectangles and draws the lines instead of the blitter where that is
faster. Since P8 all three slaves do it, from one file (`src/flight.s`); the CD32 slave also
has ExpMem now.

## The AGA flight, 18.11.2026

JOTD's slave (before P2 and P3), `profile_flight.py` and `aprof_report.py`, 150 fields per
view, in ms per frame:

| | a1200-030 F5 | a1200-030 F6 | a1200-fast F5 | a1200-fast F6 |
|---|---:|---:|---:|---:|
| frame rate | 10.67 fps | 10.67 fps | 9.67 fps | 9.33 fps |
| frame time | 93.8 | 93.8 | 103.4 | 107.1 |
| waiting for the blitter | 36.5 | 36.4 | 36.6 | 34.5 |
| the frame cap and VBL wait (`internals.md`, "Frame loop") | 27.7 | 24.1 | 1.2 | 0.5 |
| span-fill setup, $fab6 without its waits | 6.8 | 8.9 | 12.8 | 15.2 |
| everything else | 22.5 | 24.3 | 52.8 | 57.0 |

(The a1200-fast flew another mission.) What that says:

- **The frame cap binds on the 68030.** The loop waits for 6 ticks of 64 Hz a frame, so
  10.67 fps at most; a quarter of the 68030's time spins there.
- **The blitter is the wall.** The polygon filler makes one small blit per scanline span
  (650-760 a frame) and waits for each; that is 35-37 ms a frame on both machines, whatever
  the CPU, with 37-40% of the chip bus slots still free. Kept as it is, the fill alone holds
  the game under 28 fps.
- **The caches were off** (CACR $2000) on the 68030 (P3 fixes it). The slave's `CACHE` makes BaseMem
  non-cacheable, and WHDLoad uses a 68030's MMU only with `MMU/S`; without it, one
  non-cacheable area switches both caches off.
- **The stack was in chip RAM** (P2 fixes it). gs2.run's code, data and BSS load into ExpMem, but at $13d48
  the flight moves its stack onto its chip work area: stack and call instructions are 9-11% of
  the 68030's time, nearly all chip bus. The work area (600 KB: screens, buffers) is chip,
  and ExpMem has 84 KB free (P6 moves the model data).
- **The 68020/14 is CPU-bound** (52-57 ms of its own code a frame): 50 fps is for the 68030.

P1-P3 measured on the pinned mission (VERIFY builds, every cockpit shot the reference's;
fps in F5/F6; the uncapped rows patch the cap to 1 tick at $2ce, a scratch experiment):

| Slave | a1200-030 | uncapped | a1200-fast | uncapped |
|---|---:|---:|---:|---:|
| JOTD's (`CACHE`, chip stack) | 10.67/10.67 | 15.33/14.33 | 9.67/9.00 | 9.67/9.00 |
| + stack in fast RAM (P2) | 10.67/10.67 | 16.67/16.33 | | |
| + `CACHECHIP` (P3a), the release | 10.67/10.67 | 17.33/17.00 | 10.67/10.67 | 12.00/11.33 |
| + `CACHECHIPDATA` instead (P3b) | 10.67/10.67 | 17.33/16.67 | | |

On the 68030 the cap still holds the release at 10.67 fps: the frame-cap spin went from 26%
of the time to 36-38%. The a1200-fast now reaches the cap. Uncapped on the 68030, a 58 ms
frame is two thirds blitter waits. The data cache gains nothing, so `CACHECHIPDATA`, which
would also risk stale chip data the blitter wrote, is not used. With `CACHECHIP` the
instruction cache is on with or without WHDLoad's MMU, so `MMU/S` needs no mention in the
ReadMe (P3c): the MMU would only add the data cache for ExpMem.

**Time.** The simulation step is variable and follows real time: each frame dt = the 64 Hz
ticks since the last, so a faster CPU gives more frames, not faster play. With the cap at 1
tick, the mission clock still ran 3.01 s in 150 fields and 3.05 s in 152. The 6-tick cap, not
the step, is what keeps the frame rate down; dt clamps at 15 ticks, so below 4.27 fps the game
slows. Lifting the cap exposes what assumes about 10 fps:

- dt in whole 64 Hz ticks: at 50 fps frames get 1 or 2 ticks (2184 or 4369), and motion
  stutters 1:2;
- the per-frame phases B+$c68a (a blink, 5.3 Hz now, 25 Hz at 50 fps), B+$c68b and B+$c68c
  (work on alternate frames, or one frame in four);
- the 91 `muls.w dt` readers lose precision at small dt;
- the per-frame 1/65536 s the clock loses (0.08% at 50 fps).

## P4, the frame cap (CUSTOM2=1), 18.11.2026

The patches are in `internals.md` ("Slave patches", "Frame loop"). P4a: dt from the fields
since the last frame, the remainders carried (dt and the mission clock), PAL or NTSC from the
field's lines. P4b: the phases once per 6 ticks of game time. P4c: at least one field a
frame. P4e (a fixed step with interpolation) was not needed.

P4d, the coupling test (`tools/coupling.py`; the pinned mission, the same inputs at the same
game time, the a1200-030). The references are the 6-tick cap with the inputs 0-3 fields
later; outside their envelope, over mission seconds 25-90:

| Build (CUSTOM2=1) | speed | B+$d370 (falls steadily: the fuel?) | altitude | position (x, y) |
|---|---|---|---|---|
| uncapped only | reached its top 1 s early | 2766-3485 out (the references spread 424) | 16 low | 15572, 0 out (range 233938, 184251) |
| + the dither | the same | 3113-3832 out | 32 high | 4774, 576 out |
| + the step gating (the release) | as the references | 0-460 out, back inside by 70 s | 32 high | 1654, 0 out; with the inputs a field later 72, 8356 |

- **The speed was frame-coupled** (code $7c04, 1/8 of the gap a call), and B+$d370 through
  it; also the climb rate's lag and the keyboard collective. They now run once per 6
  ticks of game time.
- **The heading after a 1 s turn** depends on where the input falls among the frames: at the
  cap 8842-10283 of 65536 with the inputs 0-3 fields apart, uncapped 8979-10456; with
  `CUSTOM3=3` (3 fields a frame) 10511, `CUSTOM3=5` 9582. The positions follow the heading.
- **The hover ceiling** at full collective is 1456 with the dither, 1424 at the cap: there the
  climb rate is 2, and 2 × dt truncates to 0 a frame at the cap (without the dither,
  uncapped, 1408).
- The test covers the player only: the other position-table entries did not move in these
  90 s (entry 1, which does, is not identified). The AI, weapons and wingmen are not checked.

Frame rate, VERIFY, the pinned mission, F5/F6: a1200-030 17.33/16.67 fps (capped 10.67),
a1200-fast 11.67/11.00 (capped 10.67). The release slave: 10.67/10.67 without `CUSTOM2`,
16.33/16.33 with it (the release's own mission). Ending a mission (Alt+E, Y) returns to the
debriefing with `CUSTOM2=1` and the fast stack.

## P5, filling with the CPU, 18.11.2026

The patches are in `internals.md` ("Slave patches", "Rendering"). VERIFY builds, the pinned
mission, `CUSTOM2=1`, F5/F6 fps (one frame in 150 fields is 0.33):

| Build | a1200-030 | a1200-fast |
|---|---:|---:|
| P4 (all blits) | 17.33/16.67 | 11.67/11.00 |
| + the spans by the CPU (P5a) | 22.33/21.00 | |
| + the rectangles by the CPU | 26.33/25.33 | 12.00/10.67 |
| the spans by the blitter again on the 68020 (the release) | 26.33/24.67 | 12.33/11.67 |

The release slave on its own mission: 25.00/24.33 on the a1200-030, 12.33/11.67 on the
a1200-fast; without `CUSTOM2` both stay at the cap's 10.67 (the 68030 now spins 56-58% of the
frame there).

P5c, the pixels: `tools/screens.py` captures every drawn frame for 30 frames in each of the
cockpit, F5 and F6 views. Against the blitter build every frame is the same: at the cap on
the a1200-030, and with `CUSTOM2=1 CUSTOM3=7` (7-field frames) on both machines. On the
a1200-fast one cockpit frame of 30 differs by 4 bytes. That is graphics.library writing a
sprite's control words into the screen ("Also seen"); it lands before or after the
frame's clear depending on the drawing speed.

Tried and not kept (no measurable change):

- the span filler with its state in registers, the 4 planes unrolled and the pattern rows
  cached per field: 26.67/25.00 on the a1200-030, 12.00/10.67 on the a1200-fast (the loop
  no longer fits the 256-byte instruction cache);
- long read-modify-writes in the middles of stippled spans: 26.67/25.00;
- `CACHECHIPDATA` (data cache for fast RAM; chip RAM is never data-cached, all 68030 boards
  mark it non-cacheable): 27.00/25.67, within a frame or two of `CACHECHIP`.

Where the a1200-030 frame (38 ms) goes now (F5, `aprof_report.py`, which names the
slave's routines): the span filler 43%, the rectangles 13%, mostly chip RAM writes and the edge
words' reads; $109ba 10%; the lines $fd3c 10% (blitter waits); $e3de 7%.

**P5b (draw into fast RAM, copy once) is not done.** Its upper bound was measured: spans and
rectangles written to a fast-RAM dummy, plus a 32000-byte copy to the chip screen every
frame, gives 32.00/30.33 on the a1200-030. The copy alone is 14.5% of that frame. It would
also need exact CPU versions of everything else that draws into the view in a frame: the
lines ($fd3c, a line blit a plane), the horizon band (a line and area-fill blits), the masked
blits ($12c60, from B+$b8d8), and in the cockpit view the instrument blits (code $b0fc,
$b138, $b976, $ba16, $ba6a, $c5e8). More than 20 places also switch B+$b8dc or copy between
the three screens (code $a5e4, $1610c-$17ee6). So: at most about 20% more, at a large risk.

## P6, data out of chip RAM, 18.11.2026

Which chip RAM the flight's own code reads, from aprof's per-instruction chip time without
the custom registers (`tools/aprof_report.py`'s data, 150 fields of F5): 2.6% of the
a1200-030's time, 1.0% of it in the transform $109ba and the rest in $e3de, $1060e, $112e2,
$d5c6 and $10754. Breaking on the hot reads put them all in the block data+$922a: the
flight's model data (the front end's block, 134960 bytes up to the next, data+$9232), whose offsets
$18b8c turns into addresses at the flight's start. The slave copies it into fast memory
just before that (`internals.md`, "Slave patches"). What is left (0.4%) is $12f34, which
reads a blitter image's header, and stays.

VERIFY builds, the pinned mission, `CUSTOM2=1`, F5/F6, 600 fields a view (`SEGMENT=600`),
against a slave that makes the same copy but keeps the chip block (the copy takes about two
fields at the start, which moves the flight's timing):

| | a1200-030 | a1200-fast |
|---|---:|---:|
| the copy only | 27.58/24.42 fps | 12.92/11.75 |
| the model data in fast RAM | 28.08/25.08 (+1.8%/+2.7%) | 13.00/11.92 (+0.6%/+1.4%) |

The chip data time on the a1200-030 went from 2.6% to 0.4%. The frames (`screens.py`) are
the copy-only slave's: 90 of 90 on the a1200-030, at the cap and with `CUSTOM2=1 CUSTOM3=7`;
on the a1200-fast 89 of 90, the one the graphics.library write ("Also seen"). Against the
P5 slave they differ (the rotor's angle, the instruments) because of the moved timing.
`FASTMEMSIZE` is $130000 (it was $100000; ExpMem had 84 KB free), so ExpMem is 1.69 MB with
the Kickstart, inside the ReadMe's 2.0 MB OtherMem. If the block is larger than the buffer
or the allocation fails, the flight keeps the chip block.

The other blocks: data+$9232 (copied to a screen at code $a5a2, not in the profile) and the
heap (the screens, blitter images) stay in chip.

## P7, the cockpit view, NTSC and a busy scene, 18.11.2026

`profile_flight.py` now takes the views as keys (`VIEWS="f1 f5 f6"`, F1 the cockpit view) and
a forward flight before the windows (`FLY`); `aprof_report.py` takes the fps from the window's
seconds (PAL or NTSC). VERIFY builds, the pinned mission, `CUSTOM2=1`, 600 fields a view,
F1/F5/F6 fps:

| Slave | a1200-030 | a1200-fast |
|---|---:|---:|
| P6 | 23.13/28.12/25.04 | 12.48/12.90/11.81 |
| + the lines by the CPU (the release) | 27.12/30.20/25.88 | 13.56/13.06/11.90 |
| the same, the busy scene (`FLY=6600`, P6 first) | 21.96/27.37/23.63 → 23.88/27.71/24.29 | 10.15/10.57/10.07 → 10.32/10.65/10.40 |

- **The cockpit view was the slowest**: 37% of the a1200-030's time in blitter waits, most in
  the lines ($fd3c: 33 lines a frame, a line blit a plane, 22% of the time) and the panel's
  blit lists ($ba80, $b9aa: 15%). The lines are now drawn by the CPU (`internals.md`, "Slave
  patches"), the same pixels: 90 of 90 frames on the a1200-030 at the cap, 88 of 90 on the
  a1200-fast with `CUSTOM2=1 CUSTOM3=7` (the two the graphics.library write, "Also seen").
- **The panel by the CPU was slower** and is not kept: in longs, the mask read once for the 4
  planes, 26.87 fps against 27.12 (a1200-030), 13.15 against 13.56 (a1200-fast). Its sources,
  masks and the screen are all chip RAM, and the 68030's chip reads cost as much as the
  blits; it would need the sources in fast RAM (`tmp/` keeps the try).
- **NTSC** (`NTSC=1`): the flight runs at the same frame rates and its clock 10 s in 600
  fields; the front end picks another mission there (on the ground at the base), so the
  numbers are its own: 22.63/28.12/24.83 fps on the a1200-030 with P6.
- **The busy scene**, the pinned mission's enemy units (a Mi-8, a SAM site, missiles,
  explosions) about 140 s in: the game's own code (outside the waits and the slave's
  routines) grows from 28-29% of the a1200-030's time to 35-37%.
- **The remaining CPU work**, a1200-030, F5: the span filler 41% and the rectangles 14%
  (P6); with the lines by the CPU the transform from $109ba to $11300 10.6% (about 224 projected and 390
  other vertices a frame, no instruction above 0.7%: the divides at $11074 and $11090), $e3de
  7%. On the a1200-fast the transform is 15-16% and $e3de 8-12%: there the game's own maths
  is the limit.

## P8, the ECS and CD32 slaves, 18.11.2026

The three `gs2.run` files are builds of one source: aligning the code hunks (relocations
masked) maps every AGA place to the others, and the renderer's routines are the same code
apart from the ECS rectangles, which queue their blits. The flight's patches moved into
`src/flight.s` with the offsets per slave (`internals.md`, "The flight's patches in all
three"); the AGA slave draws the same 90 of 90 frames as P7's. The harness takes `VARIANT`
(the ECS route has its own steps, `development.md`), and on the 68000, which aprof does not
profile, it counts the presented frames (`COUNT`). VERIFY builds, the pinned mission (each
version its own), `CUSTOM2=1` unless said, fps:

| ECS | A500 (68000), F1/F5 | a1200-030, F1/F5/F6 |
|---|---:|---:|
| the cap (no `CUSTOM2`), no other patch | 4.31/4.23 | |
| `CUSTOM2=1`, no other patch | 4.39/4.17 | 15.89/16.31/14.48 |
| + the fast stack and models | 4.40/4.20 | |
| + the CPU lines | 4.37/4.09 | |
| + lines and spans, JOTD's `CACHE` | | 22.05/22.46/19.05 |
| + lines and spans, `CACHECHIP` (the release) | 4.40/4.20 (no lines) | 24.96/24.71/22.38 |
| the release without the spans | | 20.97/19.39/17.39 |
| the release without the lines | | 20.97/24.46/21.55 |

On the a1200-fast (68020, 1500 fields, F1/F5) the ECS release gives 13.15/12.45 fps, 12.48/12.45
without the lines.

| CD32, cockpit view | a1200-fast (68020) | a1200-030 |
|---|---:|---:|
| JOTD's memory (all chip) and `CACHE` | 4.99 | 5.57 |
| + `CACHECHIP` (the instruction cache was off) | 6.66 | |
| + ExpMem $130000 | 9.98 | |
| + the fast stack and models | 10.57 | |
| the release (1500 fields) | 10.92 (lines off) | 23.96 |
| the release without the rectangles | 10.48 | 22.00 |
| the release with the lines (68020) / without them (68030) | 10.98 | 23.66 |

- **On the 68000 nothing in flight is faster**: the frame rate is under the cap, the fast stack
  and models gain nothing measurable, and the CPU lines lose (the CPU spans were never a
  candidate there). The ECS slave keeps them for its 68020+ users: on the a1200-030 the ECS
  version gains 57% (F1), `CACHECHIP` 13% of it.
- **The CD32 version had no fast memory**: code, data, stack and screens all in chip, and the
  instruction cache off. ExpMem doubles its frame rate on the 68020 and quadruples it on the
  68030. It raises the slave's needs to $1ff000 chip and $1b0000 ExpMem (with the Kickstart);
  JOTD's needed $80000 ExpMem besides the chip, so a CD32 never ran it without fast RAM.
- **The CD32 rectangles first drew garbage** in the panel (and looked slower, 4.08 fps): its
  build runs the rectangle's blit list again after some rectangles, so `cf_rect` now leaves
  the list as the game's routine does.
- **Lines and spans by CPU**: as on the AGA version, the spans from the 68030; the lines from
  the 68020 in the ECS version (5% in the cockpit view there) and the 68030 in the CD32 one,
  where the 68020 gains nothing (10.98 fps without them, 10.92 with).
- **Frames** (`screens.py`, `CUSTOM2=1 CUSTOM3=10`, a1200-030, against each version's build
  without the flight patches): the ECS release draws 90 of 90 the same, the CD32 one F5 and
  F6 60 of 60 and the cockpit 27 of 30. The cockpit frames differ by 1 to 4 radar pixels, which
  the game plots by CPU (code $b774) beside the panel's blits and which follow the CPU's and the
  blitter's timing: the CD32 build without patches on the a1200-fast differs from itself on
  the a1200-030 in the same bytes and more (0 of 30). The game state (data, bss) is the same
  at every frame.

## Next

P9 of the plan is done; what is left:

1. **P9 Release 4.0b** (18.11.2026) is published (19.11.2026, tag
   `Gunship2000Enhanced-4.0b-20261118`), after a test on a real A1200 (68040/40, MMU, 32 MB
   Zorro III). That test first crashed entering flight: the game's `suba.w a1,a1` before
   `LoadView` (`internals.md`), fixed in the AGA and CD32 slaves. The three icons carry
   `CUSTOM2=1` (`release.json`'s tooltypes; the install copies the chosen icon), and the
   ReadMe's memory figures and quit key ($5d, the keypad's `*`) are the slaves'. Bump the
   version and the entry as improvements land.
2. **P4 follow-ups.** The coupling test for the AI and weapons (a mission with moving units,
   targets fired at); the joystick control mode (code $142c ramps the pitch command per step);
   `CUSTOM2` with time acceleration (`]`).
3. **P5b**, only if the rest is done (above); the cockpit panel's sources in fast RAM with it.

Not yet checked: long flights, a second flight in one session with `CUSTOM2=1`, the CPU
fills and lines in the views other than cockpit, F5 and F6 (the other cameras, the map, night),
the coupling test on the ECS and CD32 versions, and how the CD32
version switches views (its function keys are the pad's buttons).

## Also seen

- In flight, graphics.library (Kickstart code in ExpMem) writes a sprite's control words
  (a beam wait with interrupts off, then a long store) into memory that is now a screen
  buffer, probably the front end's pointer sprite. It showed as 4 stray bytes in one cockpit
  frame on line 16 (a1200-fast, with the game's blitter fills).

- The AGA slave's `_cb_dosLoadSeg` clears long 0 on every `LoadSeg`, and `set_copperlist`
  writes a copper end there for the game's `COPJMP2` to 0 (`internals.md`).
- The CD32 slave keeps `DEBUG` set, and its patch list is dead code (`_patch_gs2000`
  returns first).
