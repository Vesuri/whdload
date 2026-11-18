# Open work

Set up 18.11.2026: `src/` is JOTD's v3.1 source with three changes that make vasm assemble
it, equivalent to the shipped slaves apart from the newer KickEmu (`development.md`,
"Build"). All three variants boot to the duty roster. The AGA flight is profiled
(`development.md`, "Profiling in flight"); the target is 50 fps in flight on the a1200-030
(soft). P1-P4 of the plan are done: the VERIFY build pins the mission, the release AGA slave
keeps the flight's stack in fast RAM and turns the instruction cache on, and `CUSTOM2=1`
("Enhanced framerate") lifts the frame cap with the simulation kept at its rate.

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
  the 68030's time, nearly all chip bus. The work area (600 KB: screens, buffers) is chip;
  which parts only the CPU touches is not yet known, and ExpMem has 84 KB free.
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

## Next

P5-P8 of the plan:

1. **P5 Fill with the CPU.** Replace the per-span blits of $fab6 (and the line, clear and
   general blits $fd3c, $13832, $dda0 on the same screen):
   - P5a a CPU span fill straight into the chip screen, with masked edge words and long
     stores between;
   - P5b all of the view drawn by the CPU into a 32000-byte fast-RAM buffer, then copied
     once a frame into the chip screen; overdraw then costs fast RAM only;
   - P5c keep the blitter's dither patterns (B from D+$1ea0/D+$23a0, alternate lines) exact:
     frame-by-frame screens identical to the blitter version on the pinned mission. The
     68020/14 must not get slower (keep the blitter path for it if it does).

   This step decides whether 50 fps is reachable: the rest of the frame is 13-14 ms of the 20.
2. **P6 Data out of chip RAM.** Sort the work area's blocks (D+$922a, D+$9232 and the heap)
   into what the blitter or display uses and what only the CPU does. Move the CPU-only ones to
   ExpMem with a larger `FASTMEMSIZE` (and the ReadMe's memory line). The measure is the
   chip-bus share of "other gs2.run code" (11-13%).
3. **P7 Profile again** with the cockpit view (F1, the panel redraws), on NTSC and on a busy
   scene, and profile the remaining CPU work ($109ba transform, $e3de) if 50 fps is still
   short.
4. **P8 Release 4.0b** (18.11.2026) is set: `slave_version` gives each slave's info text and
   `$VER: Gunship2000<Variant>.slave 4.0b (18.11.2026)`, the info text credits Vesuri, and
   the ReadMe entry above JOTD's says what changed (the WHDLoad 20.1 KickEmu, the faster AGA
   flight, Enhanced framerate). `make dist` packs it; not yet published. Bump the version and
   the entry as improvements land.
5. **P4 follow-ups.** The coupling test for the AI and weapons (a mission with moving units,
   targets fired at); the joystick control mode (code $142c ramps the pitch command per step);
   `CUSTOM2` with time acceleration (`]`).

Not yet checked: long flights, and a second flight in one session with `CUSTOM2=1`.

## Also seen

- The AGA slave's `_cb_dosLoadSeg` clears long 0 on every `LoadSeg`, and `set_copperlist`
  writes a copper end there for the game's `COPJMP2` to 0 (`internals.md`).
- The CD32 slave keeps `DEBUG` set, and its patch list is dead code (`_patch_gs2000`
  returns first).
- The ReadMe's memory figures and quit key (F10) do not match the slaves ($5d).
