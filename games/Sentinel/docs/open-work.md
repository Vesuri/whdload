# Open work

Set up from Harry's and StingRay's V1.01 slave. Without the version strings the build
equals the shipped slave but for the code hunk's padding word
([development.md](development.md#the-build)). It boots to the
title, landscape 0000's overview and into the landscape on the a500, the a1200, the
a1200-040 and the a1200-060, and since B5 the 68040 and 68060 draw correctly.

## Release

2.0b (23.11.2026), not published: V1.01 with `$VER` and the info text in the slave, the
ReadMe entry above StingRay's, the self-modification fix (B5), the effect trigger's wait
(B6a), the pan step's blitter wait (B6b), the PAL/NTSC test on AGA (C8), Enhanced framerate
(CUSTOM1, on in the installed icon: D10, D11, E15, E16), the data cache in the icon
(`DCACHE`, D13) and the blitter waits always on
(V1.01's CUSTOM1 gone); `make dist` builds `SentinelEnhanced-2.0b-20261123.lha`.

## The goals

- **G1** Correct drawing on the a1200-040 (68040, MMU, Zorro III fast memory, instruction and
  data caches), and so on every fast machine, with the 68000 unchanged.
- **G2** Holding a pan (the pointer at the screen edge, or the ReadMe's S, D, L and comma keys;
  D, raw `$22`, pans right) scrolls the view continuously at 50 fps on capable machines
  (68040 and 68060), with game speed unchanged.

What is known so far is in [internals.md](internals.md#rendering-and-panning): the drawing
fault was self-modifying code in the edge scan converter, every pixel is drawn by the CPU into
chip memory, and a pan is a 128-pixel strip render followed by an 8-frame scroll-in.

## Phases and items

Items are named by phase and number (B6), sub-items by a letter (B6a); the numbers run on
across phases. Status in brackets.

### A. Harness (done)

[development.md](development.md#driving-it) describes each tool.

- **A1** The game server `tools/sentinel.py` (done): **A1a** the route; **A1b** keys, holds,
  the mouse button and moves; **A1c** the swap meter `swaps`; **A1d** `strips`, pan steps with
  the displayed buffer's hash; **A1e** the self-modification `census`; **A1f** `pointer`,
  `waitfor`, `brk` (bounded) and `front`.
- **A2** The render check `tools/render_check.sh` (done): **A2a** key pans in four directions
  against the a500's pictures; **A2b** the same pans with the pointer at the screen edges;
  **A2c** the reference is V1.01's picture on the a500, and V1.01 on the a1200-040 is the
  control that fails.
- **A3** The play check `tools/play_check.sh` (done): **A3a** boulder, robot, absorb;
  **A3b** transfer and U-turn; **A3c** hyperspace; **A3d** the exits: death by hyperspace
  with too little energy and the restart, ESC to the title and back, F10; **A3e** not
  covered: completing a landscape, the Sentinel absorbing the player, a landscape code.
- **A4** The sound patch gate, in the play check (done): the patch bytes after loading and the
  effect trigger's wait (at least 12 lines; 13 on the a500, 040 and 060). V1.01 is its
  control.
- **A5** The edge differential `tools/edgecheck.py`, in `make check` (done).
- **A6** The matrix `tools/matrix.sh` (done): the render and play checks on the a500,
  a1200, a1200-030 and a1200-040 after a change; `FULL=1` adds every cache option, the
  68020 with Zorro III memory, the 68060 lines and the two controls.
- **A7** The harness docs (done).

### B. Correct on the 68040 (bug fixes, always on; done)

- **B4** Self-modifying code census (done): only the edge scan converter's five stores, over
  4085 traced a500 fields ([internals.md](internals.md#rendering-and-panning)).
  - **B4a** (done, statically) The paths of A3e are not traced. The static code map
    (`tmp/an/flow.py`, recursive descent from the entry and the interrupt vectors: 7121
    instructions, 2155 of them never traced) finds no absolute-address store into an executed
    instruction but the edge scan converter's (`$4194`, written at `$4196`, is a data byte
    after a `bra.w`), and the only address registers loaded with code addresses in untraced
    code are the vector setup (`$3FE`..`$452`) and a table read (`$309C`). A store through a
    computed pointer in those paths would still be found only by tracing it; left alone in
    landscape 0000 for 10000 fields (a500) the player keeps 10 energy, so tracing the
    Sentinel's absorption needs a scripted route to a square it sees.
- **B5** Remove it (done): `EdgeStep`, equal to the game's code under Unicorn
  (`tools/edgecheck.py`, 200000 edges, and three deliberate faults caught).
- **B6** Other fast-CPU hazards, each checked and fixed if real:
  - **B6a** (done) The sound effect trigger's CPU-timed DMA-off wait (module `$F2E`, 11.3
    lines on the 68000, under one on the 040): `SfxDmaWait` waits 12 lines or more on every
    CPU ([internals.md](internals.md#sound)); the music and the player's resume are as on the
    68000. Not judged by ear: FS-UAE's audio hack did not fire for the trigger in the runs
    (its DMA-on is usually a later field).
  - **B6b** (done) Blitter waits: StingRay's wait at `$30C` covers the start of each blit;
    nothing waited for the last one before the pan step's swap. On a 68000 blitter-nasty
    holds the CPU until it ends; on the 030 and 040 the CPU runs alongside it. No late blit
    showed in emulation (every swap and field wait measured), but whether one is over then
    rests on bus arbitration and write buffers, so 2.0b waits for the blitter before the
    field flag is cleared (`$47AC`), as the 68000 in effect does
    ([internals.md](internals.md#rendering-and-panning)). The blits never overlap the
    CPU's column copy, and the CPU next writes a blitted buffer only in a later step, after
    `$30C`'s wait.
  - **B6c** (done) CPU-timed delays: the other `dbf` and count-down loops in the program read
    as benign (none times hardware).
  - **B6d** (done) `jmp ($10)` at `$1ED6` is never reached.
  - **B6e** (done in emulation) `movep`: 23 sites in the program (the span filler's are hot);
    the 68060 traps every one. FS-UAE's 68060 executes `movep` unless
    `--uae_cpu_no_unimplemented=true`; with it the render check matches (110 fields in pans
    against 105). The cost on a real 68060 is not measured.
  - **B6f** (done in emulation) The data cache on chip memory: with the MMU, WHDLoad's `Cache`
    and `DCache` make chip memory cacheable write-through, so a CPU read of chip memory the
    blitter or a disk load wrote since the CPU last read it can see the old bytes (the buffer
    copy at `$4822` is not one: it reads only a buffer's first 8 lines, which no blit
    writes). FS-UAE's MMU model caches chip data (real boards' chip memory is usually not
    cached); no stale read showed in the render check with `DCACHE` on the 030, 040 and 060.
- **B7** (done 23.11.2026) The full matrix (`FULL=1`, A6) with B6b's wait: every line as
  expected, the render check on all 20 machine and cache lines, the play check on the 9, and
  both controls failing. The first run found the pointer half of the render check depending
  on the CPU's speed (the 060 lines and the 040 with `DCACHE`); with the pointer entering and
  leaving the pan band in one move and `strips` counting the game's steps, the render lines
  were run again and the reference's first three lines re-recorded (frames from the middle
  of a step before); V1.01 still matches it on the a500.

### C. Measure before optimising (done)

- **C8** (done) Game time ([internals.md](internals.md#game-time), `tools/gametime.sh`): the
  vertical blank counts the object timers down at 19.9 ticks a second, and the main loop serves
  one of eight enemy slots a pass, acting on a timer that has run out (the Sentinel turns every
  200 ticks, 502 fields). Drawing delays an action until its slot comes round; it never makes
  the game run ahead of the ticks, so on faster machines the game is already a little faster:
  during a held pan a turn waited up to 17 fields for its slot on the a500 (63 in a longer
  run) and 9 on the a1200-040, and with no input the drain from 7 energy to 0 takes 765 fields
  on the a500 and 580 on the a1200-040. CIA-A timer B times only the music; there is no boot
  benchmark and no task. One bug (fixed in 2.0b, `$3C9A`): the PAL/NTSC test took AGA's chip
  ID for a line, so an NTSC A1200 ran the PAL rate, 20% fast (the Sentinel turned every 8.4 s,
  now 10.1 s as on PAL).
- **C9** (done) Profiles ([internals.md](internals.md#rendering-and-panning)): a held pan on
  the a500, the a1200 and a 28 MHz 68020 with Zorro III memory (cycle traces), the
  a1200-040 (aprof, `68040-NOMMU`), and the strip pause from `swaps` on all six machines. On
  the a500 the strip render is the pan (the span filler and the edge scanner 45%). On the
  a1200-040 the strip pause is 4 to 8 fields, the render under a third of a pan's time, and
  the scroll-in's blitter waits 40% and the field wait 20%. On the a1200-060 the pause is 3 to
  4 fields.

### D. Fast strip rendering (68020 and up, Enhanced framerate; done)

- **D10** (done) Fast memory: an optional ExpMem of 36 KB (WHDLoad's allocation, the slave
  has no buffers of its own) holds the render buffer and the edge tables; without it, or below
  a 68020, the option is off. An access census over a traced a500 run found the buffer's users
  ([internals.md](internals.md#slave-patches)): the row tables, the pan step's column
  pointers, three absolute addresses and one blitter user, the pan step's horizontal column
  copy, which the CPU now does. The span pattern tables stay at `$55000`..`$56FFF`: they are
  loaded with data the game reads there, and `SpanFill` reads only the colour table
  (`$56E60`, once a polygon) and keeps its masks in the slave.
- **D11** (done) `SpanFill` (68020, no `movep`, 16 pixels of four planes as two longs) and
  `EdgeStepF`, both on the fast tables. `tools/spancheck.py`: 30000 random polygons, 0 differ
  from the game's filler under Unicorn (three deliberate faults caught); `tools/edgecheck.py`:
  20000 edges, 0 differ for `EdgeStepF`; the render and play checks pass on the minimal
  matrix's Enhanced framerate lines. MEASURED: the strip render on the a1200-040 from 3.27 fields to
  1.53, the a1200-030 4.37 to 2.53, a 14 MHz 68020 with fast memory 5.18 to 3.74.
- **D12** (done) Profiled again ([internals.md](internals.md#rendering-and-panning)): the
  span filler is 2.2% of the 040's render (42.8% before), the rest the game's projection
  (`$11D8`, 16.5%), `$6BDA` (13.6%) and smaller routines, all chip-resident code that cannot
  move (absolute addressing, no relocation table). On a 14 MHz 68020 the slave's code is a
  third of the render, so the 68020's render is bound by the CPU. Nothing else moves.
- **D13** (decided 23.11.2026) Caches stay WHDLoad's: the slave adds no cache setting of its
  own (the original's `resload_SetCACR` instruction cache stays as it is), and the game must
  work with each of WHDLoad's options (B7). The installed icon sets `DCACHE` beside
  `CUSTOM1=1`: with the option the render buffer and edge tables are in fast memory, which
  the data cache covers. MEASURED with `CUSTOM1=1 DCACHE`: the render and play checks match on
  the a500, a1200, a1200-030, 040 and 060 (the tear check included); D held for 500 fields
  (`swaps`, from the pan's first swap), the a1200-030 476 swaps in 478 fields (462 in 470
  without `DCACHE`), the a1200-040 489 in 490 (472 in 473), the a1200-060 498 in 499 (the
  same); the render check's key pans in 118 fields on the 030 (131), 96 on the 040 (118), 84
  on the 060 (84). On real boards chip memory is not cacheable whatever WHDLoad sets, so no
  stale chip read can come of it (B6f); on a 68060 the CPU then retries each rejected
  cacheable chip access (WHDLoad's `cache.html`), which emulation does not show and is not
  measured. `ChipNoCache` is not set: it also stops the instruction cache in chip memory,
  where the game's code runs (the 040's key pans 264 fields).

### E. Continuous 50 fps panning (the same option; done)

- **E14** (done) The game's sequential loop can never pan continuously: after each step's 8
  scroll-in fields the next step's request waits for `$3764`, which the pass loop sets to 2,
  so there are at least 2 fields between steps on every CPU (MEASURED: 9.7 to 10.6 fields from
  a scroll-in's start to the next step on the a500, 040 and 060).
- **E15** (done) The pan pipelined ([internals.md](internals.md#slave-patches)): after the
  render the main loop queues the step (a copy of its strip, two copies alternating) and goes
  on to its passes and the next render; the vertical blank does the swaps and scroll steps and
  starts the queued step after a step's last swap, and the blitter's interrupt chains the
  plane blits, so the CPU renders beside them. Nothing is dropped: a step is rendered only
  after the game reads the pan from the input, as before, only 2 fields into the scroll-in
  instead of after it. The render check therefore starts a pan once `strips` counts renders
  and ends it once its last step is committed (`strips ... with ... then`), which gives the
  reference on the a500 too.
- **E16** (done) No blitter-nasty on the option's path (the scroll blits set `DMACON` `$8040`;
  `FastSetup` clears `BLTPRI`).
- **E17** (done in emulation) Acceptance: a pan held for 10 s gives a swap every field on the
  a1200-040 (472 swaps in the 473 fields from the pan's first) and the a1200-060 (498 in 499),
  every swap within the vertical blank (the render check fails a swap after line 25: the first
  2.0b build tore on a 50 MHz 68030 with `CACHE`);
  the render and play checks pass on the minimal matrix and on the full matrix's option lines
  (the a500 among them: below a 68020 the option stays off); game speed: with no input the
  Sentinel turns every 504 or 505 fields with the option, and while panning a turn waited at
  most 7 fields for its slot (C8: 9) and the drain was 612 fields on the a1200-040 (659
  without the option). FS-UAE's 040/060 timing is not hardware's (about an instruction count),
  so the 50 fps figure is still to be confirmed on a real accelerator.
