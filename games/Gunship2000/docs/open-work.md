# Open work

Set up 18.11.2026: `src/` is JOTD's v3.1 source with three changes that make vasm assemble
it, equivalent to the shipped slaves apart from the newer KickEmu (`development.md`,
"Build"). All three variants boot to the duty roster. The AGA flight is profiled
(`development.md`, "Profiling in flight"); the target is 50 fps in flight on the a1200-030
(soft). No slave changes yet.

## The AGA flight, 18.11.2026

The release slave, `profile_flight.py` and `aprof_report.py`, 150 fields per view, in ms per
frame:

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
- **The caches are off** (CACR $2000) on the 68030. The slave's `CACHE` makes BaseMem
  non-cacheable, and WHDLoad uses a 68030's MMU only with `MMU/S`; without it, one
  non-cacheable area switches both caches off.
- **The stack is in chip RAM.** gs2.run's code, data and BSS load into ExpMem, but at $13d48
  the flight moves its stack onto its chip work area: stack and call instructions are 9-11% of
  the 68030's time, nearly all chip bus. The work area (600 KB: screens, buffers) is chip;
  which parts only the CPU touches is not yet known, and ExpMem has 84 KB free.
- **The 68020/14 is CPU-bound** (52-57 ms of its own code a frame): 50 fps is for the 68030.

Experiments on the a1200-030 (scratch slaves; a `PL_W` at $2ce for the cap, the stack kept
on the process stack at $13d52, KickEmu `CACHECHIP`/`CACHECHIPDATA`):

| Slave | F5 fps | F6 fps | Blitter waits | Mission |
|---|---:|---:|---:|---|
| release | 10.67 | 10.67 | 39% | the release run's |
| cap at 1 tick | 15.33 | 14.33 | 55%, 52% | the same |
| + the stack in fast RAM | 16.67 | 16.33 | 64%, 62% | the same |
| + `CACHECHIP` (IC) | 16.00 | 16.67 | 67%, 64% | another |
| + `CACHECHIPDATA` (IC, DC) | 17.67 | 17.00 | 67%, 65% | another |

With the cap and the chip stack gone, a 60 ms frame is 38 ms of blitter waits, 7-9 ms of
span setup and 13-14 ms of everything else.

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

## Next

1. **Fly the same mission every run.** Find how the front end (`gs`) picks the mission,
   helicopter and time of day. Pin that in a VERIFY build of the slave, so slaves and machines
   compare on one flight, and make `profile_flight.py` check the cockpit against a reference
   shot. Then take the baseline again and the per-frame times (B+$b8fc at each present) for a
   frame-time histogram.
2. **The stack in fast RAM.** At $13d52 keep the process stack and still take the 2000 bytes
   from the work area (D+$2c3e += 2000), so the heap layout stays the same. Measured
   +9-14% at the 1-tick cap, and it helps every CPU. Check the flight's deepest stack fits
   the 13000-byte process stack.
3. **Caches.** `CACHECHIP` (instruction cache everywhere, BaseMem write-through) is safe;
   measure it on the pinned mission. `CACHECHIPDATA` also caches chip data: use it only if
   the CPU never reads chip data the blitter has written since (screens, the work area), shown
   by identical frames against `CACHECHIP`, or after step 6 moves that data out. Mention
   `MMU/S` in the ReadMe for 68030s with an MMU (ExpMem cached, BaseMem not).
4. **Decouple frames from steps, then lift the cap.**
   - Time from fields: present on the VBL (`COP1LC` takes effect there anyway), dt = fields ×
     32768 × 64 / (15 × 50) with the remainder carried (2796.2 a field), and the clock's add
     from the same accumulator; NTSC from 60 fields.
   - The per-frame phases from game time (every 6/64 s, as now).
   - Then the cap: at least one field a frame instead of 6 ticks.
   - The coupling test (AmigaXDev's `playbooks/fixed-time-simulation.md`): the pinned mission
     with recorded input at the 6-tick cap and uncapped, state compared at equal game time
     (position, heading, speed, fuel, weapons, targets). Fix the dt readers that drift
     (carry remainders).
   - If too many readers drift, fall back to a fixed 6-tick simulation step with the camera
     interpolated per frame (`playbooks/simulation-and-presentation.md`).
5. **Fill with the CPU.** Replace the per-span blits of $fab6 (and the line, clear and general
   blits $fd3c, $13832, $dda0 on the same screen):
   - (a) a CPU span fill straight into the chip screen, with masked edge words and long
     stores between;
   - (b) all of the view drawn by the CPU into a 32000-byte fast-RAM buffer, then copied
     once a frame into the chip screen; overdraw then costs fast RAM only.

   Prototype both, keeping the blitter's dither patterns (B from D+$1ea0/D+$23a0, alternate
   lines) exact: frame-by-frame screens identical to the blitter version on the pinned
   mission. Measure on the a1200-030 and the a1200-fast; the 68020/14 must not get slower
   (keep the blitter path for it if it does). This step decides whether 50 fps is
   reachable: after steps 2-4 the rest of the frame is 13-14 ms of the 20.
6. **Data out of chip RAM.** Sort the work area's blocks (D+$922a, D+$9232 and the heap) into
   what the blitter or display uses and what only the CPU does. Move the CPU-only ones to
   ExpMem with a larger `FASTMEMSIZE` (and the ReadMe's memory line). The measure is the
   chip-bus share of "other gs2.run code" (11-13%).
7. **Profile again** with the cockpit view (F1, the panel redraws), on NTSC and on a busy
   scene, and profile the remaining CPU work ($109ba transform, $e3de) if 50 fps is still
   short.
8. **Release 4.0b** (18.11.2026) is set: `slave_version` gives each slave's info text and
   `$VER: Gunship2000<Variant>.slave 4.0b (18.11.2026)`, the info text credits Vesuri, and
   the ReadMe entry above JOTD's says what changed (the WHDLoad 20.1 KickEmu). `make dist`
   packs it; not yet published. Bump the version and the entry as improvements land.

## Also seen

- The AGA slave's `_cb_dosLoadSeg` clears long 0 on every `LoadSeg`, and `set_copperlist`
  writes a copper end there for the game's `COPJMP2` to 0 (`internals.md`).
- The CD32 slave keeps `DEBUG` set, and its patch list is dead code (`_patch_gs2000`
  returns first).
- The ReadMe's memory figures and quit key (F10) do not match the slaves ($5d).
