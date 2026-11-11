# Internals

What is known from Codetapper's 1.3 slave (`src/BuggyBoyHD.s`), the installed files and the
race benchmark ([development.md](development.md), "Benchmark"). Sections about 1.3 describe
the slave as it was imported; what 2.0b changes is in "2.0b" at the end. All game addresses are
program offsets: the code hunk of the decrypted `bug.p`, which the shipped slave runs at
`$400` (runtime address = offset + `$400`).

## Slave header

`ws_Version` 17, flags `WHDLF_NoError|WHDLF_EmulTrap`, `ws_BaseMemSize` `$80000` (512 KB,
the whole game in chip memory), no ExpMem, no Kickstart: a direct slave. Quit key `$59`
(F10). `ws_config`: `C1` trainer ("Infinite Time"), `C2` frame rate (below; in 2.0b the
Enhanced framerate switch, "2.0b"), `C3` CD32
joypad, `BW` button wait. `resload_Control` reads `CUSTOM1`–`CUSTOM3` and `BUTTONWAIT`,
but nothing tests `CUSTOM1`, and `_SetCheat`, which would stop the high-score save, is never
called.

## Versions

The slave tells the versions apart at start:

| Version | Detected by | Path |
|---|---|---|
| Retail, DOS files (the installed archive) | `data/bug.p` exists, CRC16 `$134F` over 46328 bytes | decrypt, relocate, patch |
| Les Fous crack, DOS files | `bug.p` with CRC16 `$1084`, or `bug.o` when there is no `bug.p` | relocate, patch |
| Tenstar pack | `disk.1` boot code: `$14BC00FF` at boot offset `$156` | boot and game patch lists |
| Tenstar pack, second release | the same longword at `$166` | its own lists |
| The Story So Far compilation | `$08280002` at `$102` | its own lists |

Anything else is `TDREASON_WRONGVER`. The installed archive also has a 3392-byte `bug.o`
(a hunk file); because `bug.p` is checked first, it is not loaded.

## How the DOS version loads

1. `resload_LoadFileDecrunch` of `bug.p` to `$3E0`: its 32-byte hunk header ends at
   `$400`, where the code starts. Program offsets below are from `$400`; the `bug.p` file
   offset is the program offset + `$20`.
2. Retail only: decrypt `$2A6C` longwords from `$400` in place. Each nonzero longword gets
   the key `$49946CFD` added, its 32 bits reversed (`roxl`/`roxr` loop) and the key
   subtracted; zero longwords stay.
3. Relocate: the zero-terminated table at program `$A9BC` lists offsets of longwords that
   get the load address added.
4. The patch list below, plus `PL_BugOP_CD32` with `CUSTOM3`. The trainer list
   `_PL_BugOP_Tr` (initial time 0 at `$64E`, no time decrement at `$1626`, no lap bonus at
   `$1E4E`) is assembled but never applied.
5. The `trap #15` vector `$BC` points at the high-score save, the keyboard
   handler is installed (`keyboard.s`), a one-word copper list `$FFFFFFFE` at `$3CC`, colour
   0 black, DMACON `$83D0`, then `jsr $400`.

The game's `AllocMem` calls get a bump allocator from `$10000`, cleared, 16-byte aligned.
Running past `$80000` writes `MEM ERR ` at address 0 and quits. ExpMem is 0 and the stack is
at the top of BaseMem, so everything, code included, is in the 512 KB of chip memory.

## Patches (DOS version)

Program offsets (from `$400`).

| Offset | Original | Patch |
|---|---|---|
| `$8`, `$24`, `$40`, `$5C` | `AllocMem` calls (67102, 240000, 63072, 57088 bytes; the source comment says 63702) | `jsr _AllocMem` |
| `$D4` | | `_LoadHighs`: clear the table (`$5D4`), load `BuggyBoy.highs` (640 bytes, XORed with a falling counter) to `$8EA4` |
| `$5E0` | | `'IAN'` fills the default high-score names |
| `$1C86`, `$1C8A` | `lea $FFFF824C,a2` (Atari ST palette) | `$DFF18C`, `nop nop` |
| `$2572`, `$257C`, `$259E`, `$25A8`, `$2610`, `$261C` | dos.library open, check, `Delay`, `Disable`, `CloseLibrary` | `nop nop` |
| `$260A` | `move.l #200,d1` | `jsr _Delay`: 1 s, or until a button with `BUTTONWAIT` |
| `$2622` | error exit (no memory, file error) | `jmp _debug` |
| `$262E` | the file loader | `jmp _LoadFile`: `resload_LoadFileDecrunch`, path before `:` stripped |
| `$2682` | `move.l (a1,d0.w),$DFF080` | `jsr _LockFrameRate` (below) |
| `$29C2` | `clr.b (a0)` after name entry | `trap #15`: the same `clr.b`, then save the table unless the trainer flag is set |
| `$4B9A`, `$4DA6`, `$6696` | INTENA values `$4000`, `$C020`, `$C000` | `$C008`, `$C028`, `$C008`: PORTS enabled for the keyboard |
| `$4BAA`, `$4C72` | BPLCON0 `$4000` | `$4200`: colour bit set (1.1) |
| `$4DB0` | `lea $DFF000,a0` | `jsr _CountFrames`: count one, then the same `lea` |
| `$6650`, `$6674` | `move.w $1E(a0),d0; and.w d4,d0` | `jsr _SoundFixOrig`: the same test, retried for up to 8 raster lines (the lockup when hitting rocks) |
| `$2538` (`CUSTOM3`) | joystick store | `jmp _CD32_Read`: CD32 pad red = fire, forward/reverse = up/down, reverse+forward+play = quit |

The disk versions get the same kinds of patches at absolute addresses (the game loads at
`$70000`), with their own loaders through `resload_DiskLoad` (`$18A8`-byte tracks) and
their trainer lists, which are applied unconditionally. The second Tenstar release has no frame-rate patch and an empty
trainer list (commented out in the source).

## Frame rate control (1.3)

1.3's option, as imported; 2.0b replaced it ("2.0b", "The frame rate option").

`_CountFrames` runs in the level-3 handler, once per field (only VERTB is enabled).
`_LockFrameRate`, before the game writes COP1LC, waits until the count since the last swap
reaches N and resets it. The game's own wait for the next field follows the swap, so a frame
takes at least N fields: the cap is 50/N fps, not the 50/(N+1) the labels assume.

| `CUSTOM2` | N | Label | Cap (measured on the a1200-030) |
|---|---|---|---|
| 0 ("Default speed") or above 7 | 4 | 10 fps | 12.5 fps |
| 1 | 1 | 25 fps | none: the game's own rate (the 1.2 behaviour) |
| 2 to 7 | `CUSTOM2` | 17, 13, 10, 8, 7, 6 fps | 50/N: 25, 16.7, 12.5, 10, 8.3, 7.1 |

The A500 never reaches the default cap (it draws a race frame in 4.3 to 5.7 fields), so the
lock changes nothing there. On a fast Amiga the default runs the game at 12.5 frames a
second, about 39% faster than the A500's 9 in the benchmark window. `CUSTOM2=5` ("8fps") is
the one that gives 10. The wait is a busy loop on the counter.

## Frames and time

The race loop is `$158`–`$1AC`, once per frame, with no other clock:

| Step | Offset | What |
|---|---|---|
| 1 | `$153E` | the game logic: input, speed, the road phase, objects, timers, and the road projection `$2352` (below) |
| 2 | `$6716` | the road: `bra` to `$9D6A`, a CPU renderer |
| 3 | `$1E2` | clears the back buffer (blitter, then CPU) |
| 4 | `$33BE` | the objects (CPU-masked sprites, `$3D94`) and blits |
| 5 | `$448A` | starts with the HUD digits (score, time, speed); more drawing after |
| 6 | `$2672` | the swap: toggles `$9818` bit 2 (which of the two copper lists in `$670E` shows), the 1.3 lock, COP1LC, then `$4B7C` |
| 7 | | pause and quit checks, back to step 1 |

`$4B7C` waits for the field counter `$66D8` to change. That counter is the only time source
the game has: the level-3 handler (`$4DAC`) increments it once per field and runs the
4-channel sound sequencer, and nothing but `$4B7C` reads it. There are no CIA timers or beam
reads. So every quantity advances once per frame, and game speed is the frame rate:

- The time display `$9922` counts down once every 12 frames (`$9924`).
- The road phase `$987C` (below) moves per frame by a step from a table.
- Objects move one depth slice per segment crossed.

The logic is cheap: `$153E` is 2.4% of the A500's time, about 0.13 fields per frame, and
0.014 fields on the 68030. The drawing is everything else.

### The road and the objects

- **Phase and segments.** Forward motion is a phase `$987C` in units of 1/8 segment, used as
  0, 2, 4, 6. Each frame (`$185E`) it gains `2 × table[$804C + (speed & $70) + cycle]`, the
  cycle `$98B4` stepping through 8 entries. At 8 or more it is cleared, not reduced, so the
  overshoot is lost, and the segment parity `$987A` toggles (the stripe colours) and
  `$98C0` flags a new slice. `$987E` (phase × 221) and `$9880` (phase and parity × 96) are
  derived for the renderers.
- **Speed bands.** The step table gives per-frame steps of 0, 0–2, 0–2, 2, 2–4, 4, 4–8 and 8
  phase units for the 8 bands: in the top bands the world moves a whole segment every
  frame, the phase stays 0, and motion is shown only by the objects stepping a slice and the
  stripes swapping.
- **Road slices.** The road is 14 perspective slices; `$7DAA` holds their row counts for each
  of the 4 phases (16 bytes a phase; the last slices grow from 7 to 25 rows). `$2352`
  builds the per-row table at `$9B22`–`$9CC9` from them, the per-segment curves at
  `$9942` and the lateral position `$9890` (which steps by up to ±60 per frame when steering). The road
  renderer draws 96 + 5 rows from that table, every row, every plane, with `move.w`.
- **Objects** are codes in 32-byte slice rows from about `$9980`, one row per depth slice;
  they shift a row when a new slice starts. The object routine draws each at the position
  and pre-scaled size of its slice.
- **State block.** The logic writes `$9860`–`$9D6F` (1.3 KB; also `$8E70`) and the drawing
  reads it. The drawing writes some too: the object routine `$8B40`–`$8B4F`,
  `$8E70`–`$8E8F`, `$9880`–`$989F`, `$98D0`–`$98EF` and `$9930`; `$448A` `$8E70`–`$8E8F` and
  `$9920`–`$992F`; the clear `$98D0`–`$98DF`. Some of it is game logic: `$41E2`, inside the
  object routine, sets `$9930` to 30 or 60 when the lateral position passes ±280 and clears
  `$98EE`.

## Memory and DMA

From the benchmark's chip-bus records:

| Memory | Pointer | Requested | DMA | CPU per field (030) |
|---|---|---|---|---|
| program `$0`–`$AFFF` | | (no type in the hunk) | none | code and state |
| alloc 1, 67102 bytes | `$265A` | chip | copper list, both screens (4 planes of 8000 bytes), blitter C and D | 3,700 reads, 9,400 writes |
| alloc 2, 240000 bytes (`graphics`) | `$982E` | chip | blitter A, B, C sources | 840 reads |
| alloc 3, 63072 bytes (COURSES.DAT) | `$9822` | public | none | 70 reads |
| alloc 4, 57088 bytes | `$982A` | chip | audio | 1,100 reads (the road's source) |
| stack, top of BaseMem | | | none | 190 reads, 190 writes |

The game asks for chip only where DMA needs it; only the slave's single BaseMem puts the
program, COURSES.DAT and the stack in chip as well. No DMA in the benchmark window reads
the program, so the program can run from fast memory (the experiment in
[development.md](development.md)); other screens (title, menus, name entry) are not yet
checked.

## Performance

The race benchmark's 200-field window (Offroad, joystick up), cycle-exact traces; the 68030
without its MMU (WHDLoad does not use it without its `MMU` option, so the cache state is the
same). Work per frame excludes the waits.

| Machine | Slave, options | fps | Fields per frame | Work per frame, fields: median (min–max) |
|---|---|---:|---|---|
| a500 | 1.3, default | 9.00 | 5 ×14, 6 ×21 | 5.09 (4.34–5.69) |
| a1200 | 1.3, `CUSTOM2=1` | 12.50 | 4 | 3.57 (3.18–4.01) |
| a1200 | 1.3, `CUSTOM2=1`, `CACHE` | 24.00 | 2 ×86, 3 ×9 | 1.74 (1.46–2.12) |
| a1200-030 | 1.3, default | 12.50 | 4 | 3.12 (2.74–3.44) |
| a1200-030 | 1.3, default, `CACHE` | 12.50 | 4 | 1.75 (1.52–1.94) |
| a1200-030 | 1.3, `CUSTOM2=1` | 13.25 | 3 ×12, 4 ×40 | 3.12 (2.74–3.44) |
| a1200-030 | 1.3, `CUSTOM2=1`, `CACHE` | 25.00 | 2 | 1.60 (1.36–1.94) |
| a1200-030 | program in fast, I and D caches, `CUSTOM2=1` | 25.00 | 2 | 1.34 (1.15–1.72) |

- **Caches are off** on the 68020 and 68030: the slave sets no cache policy and WHDLoad
  without the MMU then disables both. The instruction cache alone (`CACHE`) halves the
  work on both CPUs; no glitch was seen.
- **The chip bus decides.** The 68020/14 and the 68030/50 are within 10% of each other.
  With the program in fast memory, the work splits per frame: road 0.41 fields, objects
  0.40, `$448A` 0.31, clear 0.23, logic 0.01. What remains is the CPU's chip accesses to the
  screens (about 26,000 a frame: 18,800 writes, 7,400 reads, at about 30 cycles each) and
  reads of the graphics in alloc 2 and 4 (about 4,000).
- **Word-wide drawing.** The road writes `move.w` (about 8,200 a frame); the object
  plotter does `and.l`/`or.l` at word-aligned addresses, two bus accesses each on a
  32-bit chip bus. Long-aligned 32-bit writes would halve the road's accesses.

## 2.0b

`src/Enhanced.s`, included by `BuggyBoyHD.s`; the hooks in `BuggyBoyHD.s` are
`_EnhInit` after `resload_Control`, `_EnhDest` for the load address, `_EnhGo` for the
start, `_AllocMem`, and `_LoadHighs` made relative to the program base.

- **The gate** is `WHDLTAG_ATTNFLAGS_GET`: a 68020 or better takes the enhanced path, a
  68000 or 68010 runs 1.3's code. The disk versions never reach it.
- **ExpMem** is optional, `$81000` bytes (`$A1000` in the VERIFY build; WHDLoad wants a multiple of `$1000`). It counts as fast memory unless it is below
  `$200000` (chip) or in `$C00000`–`$DFFFFF` (slow memory on the chip bus). Fast ExpMem
  holds:

  | Where | What |
  |---|---|
  | base | the program (to `$B4D0` with its relocation table; the hunk header in the 32 bytes before). The base is the first 64 KB boundary at least `$20` bytes into the ExpMem, so the program does not cross one, as at `$400` in chip (word-sized address arithmetic would break there) |
  | base + `$C000` | the game's public allocations: COURSES.DAT (63072 bytes) |
  | base + `$1C000` | the slave's buffers: saved state, the road's screen and source, the blit queue, and from + `$17800` a copy of alloc 2 (240000 bytes, the graphics; only with fast ExpMem) |
  | the top `$2000` bytes | the stack (SSP set to the top before `jsr` to the program) |

  Without fast memory the base is the ExpMem's start and only the buffers are there.
- **Alloc 1 starts 2 bytes later** (on any 68020 or better). It holds the screens at
  + `$C1E` and + `$891E`, which were 2 bytes off a longword, so every longword access
  to them (the clear's `clr.l`, the HUD's and the objects' `and.l`/`or.l`) took two chip
  accesses. Its DMA (copper list, bitplanes, blitter) needs only word alignment.

  Chip allocations stay with 1.3's bump allocator from `$10000`. The program's only
  absolute references outside its hunk (`$2A5E`–`$2A88`: `$D32C`, `$D46C`, `$D5AC`,
  `$D5AE`) are not relocated, so they stay in chip wherever the program runs.
- **Caches** (`_EnhCache`, `resload_SetCPU`): instruction and data caches, ExpMem and
  slave copyback. BaseMem is write-through, because without the MMU a non-cacheable region
  turns every cache off (WHDLoad's cache.html). The 68030 does not data-cache chip memory
  anyway. On a 68040 or 68060 with the program in fast memory BaseMem is non-cacheable,
  since those CPUs slow down on cacheable chip accesses. The 68060 also gets the branch
  cache and superscalar dispatch.
- **The frame rate option** (`C2:B:Enhanced framerate`, `CUSTOM2`) replaces 1.3's list.
  The game's logic runs at 10 Hz on every machine and with either setting:
  `_LockFrameRate` waits for 5 fields from swap to swap (1.3's N fixed at 5) on every
  screen outside the race, and in the race on the 68000 and 68010 and without an ExpMem.
  In the fixed tick, `CUSTOM2` non-zero draws the frames between ticks (as many as the
  machine manages); zero makes `_PreDraw` wait until the next tick is due, so every frame
  is a tick frame: 10 fps, the same logic and drawing sequence. 1.3's default (N = 4) ran a
  fast Amiga's game at 12.5 Hz.
- **Program base.** The level-3 vector `$6C` holds the base + `$4DAC`. On the a1200-030
  setup the base is `$980000` (`$960000` in the VERIFY build).

### The fixed tick

With a 68020 or better and any ExpMem (for the buffers), `_PL_Tick` changes the race loop:

| Offset | Original | 2.0b |
|---|---|---|
| `$138` | `lea $DFF000,a0` (race setup, on every way into the loop) | `_RaceInit`: the first pass runs the logic, and a tick is due at once |
| `$158` | `bsr $153E` (logic), `bsr $6716` (road), `bsr $1E2` (clear) | `_PreDraw`, then the road and the clear |
| `$16C` | `bsr $2672` (swap), `tst.w $9874` | `_PostDraw` |
| `$2682` | (1.3's lock) | `_SetCop`: no wait in the race loop's swap; the 10 fps lock everywhere else |

- **The tick** is due every 5 fields of the game's field counter `$66D8`. A frame that
  starts when a tick is due is a *tick frame*: it draws the committed state, writes and all,
  as the original drew after each logic step, and the logic runs at the start of the next
  frame. A tick frame more than a tick late starts the count again. So the logic and the
  drawing's writes to game state happen in exactly the original order, once per tick; the
  state at each logic step is byte-identical to 1.3's at `CUSTOM2=5` (10 Hz) over 600
  ticks of the benchmark route.
- **A frame between ticks** saves the state, sets a pose, draws, and restores the state
  before the swap; then it goes straight back to the loop's start, so the checks after the
  swap (race end `$9874`, the right button, the left button's delay) run on tick frames
  only. Saved: `$9860`–`$9D6B` (the logic's block), `$8B40`–`$8B4F` and `$8E70`–`$8E8F`
  (the drawing's own counters and HUD state), and the two COURSES.DAT words the object
  routine animates each frame (`$3418`: `($9826)` + `$D70` and + `$1250`). The VERIFY
  build compares the whole program and COURSES.DAT after each such frame
  (`tools/verify.py`); nothing else changes but what the level-3 handler writes (`$66D8`,
  the sound channels `$4EDC`–`$4F13`).
- **The pose** (`_Pose`). The logic step after a tick frame saves the state first (S_prev,
  the state that frame showed); the live state is then S_next. A frame n fields (1 to 4)
  after the tick frame's due field shows n/5 of the way from S_prev to S_next:
  - forward: the position is phase plus segment. A tick moves it at most one segment,
    since a crossing clears the phase. The position is rounded to the renderers' even
    phases. Before the crossing the frame uses S_prev's state with that phase, after it
    S_next's. `$987E` and `$9880` are derived again from it.
  - lateral `$9890`: interpolated, unless it changed by more than 128 in the tick (a jump).
    Steering moves it by up to ±60 a tick at speed (the step table at `$810C`: steering
    state × 8 + speed / 16), plus the curve's drift.
  - the projection `$2352` is run again, for the row tables.
  - horizon `$98DE`: set so that the clear's step (`$98DC` × `$98DA`) lands n/5 of the
    way, wrapped to 0–639.

  A backward phase in the same segment (a new race) shows S_next unchanged. Objects, the
  HUD and the player's sprite are the chosen tick's.
- **The road in fast memory** (with fast ExpMem; `_PL_Road`). The race loop's road draws
  into a screen in the work area, reading a copy of alloc 4 made at each race start
  (`$9D6A` gives it that screen, `$9D78` the copy; the road's other callers, `$2CC0` and
  `$32F4`, draw as before). `_CopyRoad` then writes rows 104 to 199 of the 4 planes to the
  back buffer as aligned longwords. The road writes every word of those rows and reads
  only what it wrote in the same row; the VERIFY build draws it both ways each frame and
  compares (`tools/verify.py`: no difference in 801 frames).
- **The clear queued to the blitter** (with fast ExpMem; `_PL_Queue`). The clear's blits
  are recorded instead of run: at the frame's start (the back buffer is free once the
  swap's field wait is over) `_QSky` queues the sky's planes 0 and 2 (rows 0 to 83, 1.3's
  two blits); after the pose `_QClear` runs the clear's own code from `$27E` (the horizon
  step, `$98D2` and `$98DE`, which only the logic reads, and the backdrop, rows 84 to 103,
  up to 16 blits) and adds its blits, restarting the queue if it ran dry. The CPU clears
  the sky's planes 1 and 3 after the road's copy, as 1.3 does (`_CpuSky`). `$2D4` gives that code a register
  block in the work area instead of `$DFF000`, and its 16 waits (`$318`–`$5B6`) queue the
  blit set up so far. The blitter interrupt (`$4DB6`, in the level-3 handler, which
  otherwise counts every level-3 interrupt as a field) starts each next blit while the CPU
  runs the logic, the pose and the road in fast memory; `_QSync` waits for the last before
  the objects, the next to use the blitter. All the later blit code sets every register it
  uses. The VERIFY build runs 1.3's clear after the queued one from the same horizon and
  compares rows 0 to 103 (`tools/verify.py`: no difference in 1317 frames).
- **The CPU's masked plotters** (`_PL_Plot`, on any 68020 or better with ExpMem). Each read
  the screen twice and wrote it twice per plane (`and` then `or` in place); the
  replacements read and write each word or longword once, leaving every register and
  flag as the original does:

  | Offset | Original | 2.0b |
  |---|---|---|
  | `$3DC4` | the column plotter's loop (`$3D94`, `$3D60`: one word column, bottom up) | `_PlotColumn` |
  | `$41A4` | the player's buggy (`$418C`: 40 rows of 4 longwords, from alloc 2 + `$D3A8`) | `_PlotBuggy` |
  | `$4A94` | the 8 rows of a HUD character (`$4A70`) | `_PlotText` |

  With fast ExpMem, `_RaceInit` copies alloc 2 to fast memory and, between `_PreDraw` and
  `_PostDraw`, the column plotter reads its source from the copy, unless the source spans
  overlap the buggy's 4 planes. The logic (`$1434`) animates the buggy's plane 1 in place
  (alloc 2 + `$F2E8`, 1600 bytes): over 3000 fields of the route it is the only part of
  alloc 2 that changes (the VERIFY build compares the rest every 16th frame). The buggy
  reads its source from chip. `tools/plotcheck.py` runs the original loops (from a chip dump)
  and the replacements in Unicorn's 68020 on random registers and memory (3000 cases each)
  and compares registers, condition codes and memory: no difference.
