# Performance

The original's baseline (resolution plan step 1), measured 26.11.2026 on the
reconstructed slave 1.3 (byte for byte Psygore's) with the Aminet 8-channel version ($c4dc,
the AGA drawer), from commit 569e1934's tools plus `tools/baseline.sh` and
`tools/frametime.py`. Every figure is MEASURED in FS-UAE unless marked DERIVED; none is from
real hardware.

## How

    tools/baseline.sh frames MACHINE tmp/base/frames-MACHINE   # frame counts
    tools/baseline.sh aprof  MACHINE tmp/base/aprof-MACHINE    # cycle profiles

- Two deterministic boots (`WARP=1 DETERMINISTIC=1 JOY0=none`) into level 1 with mouse
  control (`ab3d.py level`). The first measures standing at the start in the small view
  (500 fields), then in full screen (500), then the scripted walk `walk` in the small view
  (550). The second measures the walk in full screen (550).
- `frames` counts the `drawPt` swaps on the normal FS-UAE with the machine's own setup.
- `aprof` runs `$FSUAE_APROF` and profiles every field (`ab3d.py aprof`). aprof needs a CPU
  without an MMU model, so its machines are the a1200-fast setup with `EXTRA_ARGS`:
  - the 68020 is the a1200-fast as it is;
  - the 68030 is `--cpu=68EC030 --uae_cpu_frequency=50000000 --uae_cpu_data_cache=true`;
  - the 68040 is `--cpu=68040-NOMMU --uae_cpu_frequency=25000000 --uae_cpu_data_cache=true`,
    on the a1200-fast's Zorro II fast memory.
- A frame is the fields from one swap to the next. Its work is those fields' time less the
  frame wait: the main loop's INTREQR poll at $32fe ([internals](internals.md#the-frame)).
- The 68020 reference is the a1200-fast: the plain a1200's 2 MB cannot hold the slave's
  1.4 MB of ExpMem (WHDLoad: "Can't allocate ExpMem").

## Frame rates

Frames shown a second; the walk's histogram is fields a frame.

| Machine | Start, small | Start, full | Walk, small | Walk, full |
|---|---|---|---|---|
| 68020 14 MHz, a1200-fast | 10.00 | 10.00 | 9.96 (4:43 5:21 6:45) | 9.93 |
| 68020, aprof | 10.00 | 10.00 | 9.96 (4:42 5:22 6:44) | 9.95 |
| 68030 50 MHz, aprof (68EC030) | 16.67 | 16.67 | 19.71 (2:98 3:117) | 19.65 |
| 68030, a1200-030 setup | 25.00 | 25.00 | 31.57 (1:148 2:194 3:4) | 32.60 |
| 68040 25 MHz, aprof (NOMMU) | 25.00 | 25.00 | 25.00 (2:274) | 25.00 |
| 68040, a1200-040 setup | 16.67 | 16.67 | 19.38 (2:89 3:123) | 19.62 |

- Both views run at the same rate: both draw the same 96x80 frame.
- The a1200-030 setup's 25 fps is an emulation artefact. With `--uae_mmu_model=0` added
  to the same setup the start gives 16.67, the aprof figure. With `--uae_uaeboard=min` it
  still gives 25 (300 fields each). The game runs with the data cache on (CACR $2111), and
  FS-UAE's 68030 MMU model caches Chip RAM data, which no board does (AmigaXDev
  `reference/headless-fsuae.md`). The 68030 figures to compare against are aprof's.
- The a1200-040 setup's MMU core sends every access through the Chip bus delays, and its
  instruction timing is not hardware's (the same doc). Its memory is Zorro III, against
  aprof's Zorro II. The 040 figures to compare against are aprof's, and neither predicts
  a real 68040.

## Work a frame

ms of CPU work a frame, less the frame wait, from aprof.

| CPU | Start, small: mean | Walk, small: mean / p50 / p95 / max | Walk, full: mean / p50 / p95 |
|---|---|---|---|
| 68020 | 98.4 | 92.9 / 96.5 / 113.7 / 120.2 | 92.8 / 96.1 / 113.0 |
| 68030 | 42.7 | 42.9 / 42.0 / 53.9 / 60.1 | 41.2 / 41.8 / 49.2 |
| 68040 | 32.2 (30.6 DERIVED) | 31.5 / 32.3 / 36.5 / 38.1 (30.5 DERIVED) | 31.6 / 32.3 / 36.6 |

The frame rate steps by whole fields (20 ms): 98 ms of work makes five fields a frame on the
68020, 43 ms three on the 68030, and 32 ms two on the 68040.

DERIVED: on the 68040 the frame wait's own instructions collect some of aprof's `gap`.
A fit of each field's gap to its wait and work instruction counts puts 1.1-1.6 ms a frame on
the wait, and the bracketed figures leave it out. On the 68020 and 68030 the fit gives the
wait none.

### What gap is

aprof's `gap` is time outside instruction bodies, charged to no PC: interrupt entry, and on
the 68020/030 core the memory wait states plus the per-instruction tax that
`wait_memory_cycles()` adds after an instruction. On the 040 core it is instructions that
advanced no time. It is 13-15 ms of a frame on the 68020 and 68030 and 19 ms on the 68040.
The shares below share it out by each category's instruction count (DERIVED).

## Where it goes

Walk, small view, % of the work with gap shared by instructions (DERIVED). The
categories are `ab3d.py CATEGORIES`, by the source-file map in
[internals](internals.md#renderer-routines).

| Category | 68020 | 68030 | 68040 |
|---|---|---|---|
| Walls | 41.5 | 41.8 | 43.0 |
| Floors and ceilings | 25.3 | 25.8 | 26.8 |
| Objects | 11.6 | 10.8 | 8.3 |
| Geometry and visibility | 8.6 | 7.6 | 6.4 |
| Sky (`backrout`) | 3.5 | 5.9 | 8.4 |
| Game logic | 5.6 | 4.6 | 4.0 |
| Gun | 2.6 | 2.8 | 2.6 |
| Slave and WHDLoad | 1.1 | 0.7 | 0.5 |
| Interrupts (VBL, keyboard, music) | 0.2 | 0.1 | 0.0 |

Standing at the start the walls take a larger share (46%) and the floors a smaller one (22%).

The hottest routines (walk, small view, % of the time charged to PCs, MEASURED;
`chip` is the share of the routine's time spent on the Chip bus):

| Routine | 68020 | 68030 | 68040 |
|---|---|---|---|
| `acrossscrngour` $20ff4 (Gouraud floor span) | 6.7, chip 35% | 8.2, chip 69% | 13.1, chip 100% |
| `drawwallPACK0-2` $1ca80-$1cab8 (wall strips) | 15.5, chip 36-44% | 20.0, chip 68-69% | 31.9, chip 100% |
| `backrout` $18ffa (the sky writer) | 3.6, chip 70% | 7.5, chip 88% | 16.9, chip 100% |
| object search $21160-$21234 | 10.1, chip 0% | 8.2, chip 0% | 0 (all in gap) |
| `CalcAndDraw` $1b660, `pastscrinto` $1a6fa (wall set-up) | 10.6 | 9.1 | 7.5 (`pastscrinto` 0, all in gap) |

The pixel writers spend most of their time waiting for the Chip bus: about 40% on the 68020,
69% on the 68030 and all of it on the 68040. On the 68040 core
the register-only loops cost nothing charged to their PCs: their time is in gap. Every view pixel is a word write into the copper
list. That supports the plan's chunky buffer in fast memory; step 4's measurements test it.

## The display skeleton

Enhanced resolution's step 4 (plan, [internals](internals.md#the-1x1-display)), measured
26.11.2026 the same way: `WHD_ARGS=CUSTOM5=1 tools/baseline.sh aprof MACHINE OUT`. The
renderer is still the original's, now drawing into copper lists in fast memory; each frame
is then converted to pens 2x2 or 3x3 (`convert`) and through `c2p1x1_8_c5_030_2` a row at a
time (`c2p`) onto the new screens. `ab3d.py SLAVE_CATEGORIES` names the slave's routines
from the release build's listing.

Frames a second, and work a frame in ms (mean), against step 1's:

| CPU | Start, small | Start, full | Walk, small | Walk, full |
|---|---|---|---|---|
| 68020 | 7.14 (139.2; was 10.00, 98.4) | 5.56 (168.4) | 7.04 (134.7; was 9.96, 92.9) | 5.79 (164.3; was 9.95, 92.8) |
| 68030 | 16.67 (48.6; was 16.67, 42.7) | 16.67 (52.1) | 17.40 (47.2; was 19.71, 42.9) | 16.70 (51.2; was 19.65, 41.2) |
| 68040 | 16.67 (45.2; was 25.00, 32.2) | 12.50 (67.6) | 19.22 (43.3; was 25.00, 31.5) | 12.68 (66.8) |

ms a frame standing at the start, charged to the routines' PCs (MEASURED), and with gap
shared by instructions (DERIVED, in brackets):

| CPU | c2p, small | c2p, full | convert, small | convert, full | walls + floors, small (step 1) |
|---|---|---|---|---|---|
| 68020 | 30.2 (34.5) | 64.9 (65.3) | 13.0 (14.6) | 18.6 (18.7) | 55.8 (60.4), was 58.1 (67.0) |
| 68030 | 10.2 (13.8) | 22.1 (22.4) | 3.7 (5.0) | 5.2 (5.3) | 16.3 (20.3), was 20.3 (29.3) |
| 68040 | 5.1 (17.2) | 12.9 (38.8) | 0 (4.6) | 0 (6.0) | 3.3 (16.0), was 9.4 (22.5) |

- The c2p is the largest new cost: 30720 pixels a frame in the small view, 69120 in full
  screen. Full screen costs about twice the small view, not the 2.25 of its pixels.
- With the lists in fast memory, walls and floors on the 68030 take 20.3 ms (DERIVED)
  where they took 29.3 with every pixel a chip write, and on the 68040 16.0 where they
  took 22.5. On the 14 MHz 68020 they change less (60.4 DERIVED, was 67.0): its fast
  memory is not much faster than chip for these writes.
- On the 68040 most of the time is in aprof's gap, so its DERIVED figures carry the most
  uncertainty, and this machine's fast memory is Zorro II. Choosing the c2p per CPU
  (`c2p1x1_8_c5_040` on the 68040) is step 7's.
- The conversion and the 2x2 or 3x3 copy go away at step 5, where the writers draw pens at
  1x1, and their place is taken by drawing 4x or 9x the pixels.

## The 192x160 small view

Step 5 (plan, [internals](internals.md#the-1x1-renderer)), measured 26.11.2026 the same
way with the release build: `WHD_ARGS=CUSTOM5=1 tools/baseline.sh aprof MACHINE OUT`. The
game's own writers draw the small view at 192x160 into the lists (4x the pixels), each
frame is converted to pens 1x1 (`convert`, `_ds_one`) and through the same c2p. Full
screen is unchanged from step 4 (5.56-5.60 / 16.67-16.70 / 12.50-12.59 fps).

Small view, frames a second and work a frame in ms (mean), against step 4's and step 1's:

| CPU | Start | Walk |
|---|---|---|
| 68020 | 3.85 (245.5; step 4 7.14, 139.2; step 1 10.00, 98.4) | 3.85 (251.2; 7.04, 134.7; 9.96, 92.9) |
| 68030 | 10.00 (82.9; 16.67, 48.6; 16.67, 42.7) | 10.73 (86.1; 17.40, 47.2; 19.71, 42.9) |
| 68040 | 12.50 (72.7; 16.67, 45.2; 25.00, 32.2) | 11.66 (75.3; 19.22, 43.3; 25.00, 31.5) |

ms a frame standing at the start in the small view, charged to the routines' PCs
(MEASURED), and with gap shared by instructions (DERIVED, in brackets):

| CPU | walls + floors (step 4) | convert (step 4) | c2p | slave | objects |
|---|---|---|---|---|---|
| 68020 | 116.4 (127.4), was 55.8 (60.4) | 34.6 (38.7), was 13.0 (14.6) | 30.3 (34.6) | 17.5 (19.1) | 9.9 (10.9) |
| 68030 | 33.7 (42.3), was 16.3 (20.3) | 9.7 (13.0), was 3.7 (5.0) | 10.3 (13.6) | 4.9 (6.1) | 2.8 (3.6) |
| 68040 | 4.4 (34.1), was 3.3 (16.0) | 0 (11.2), was 0 (4.6) | 4.9 (16.6) | 0.7 (4.8) | 0.1 (2.7) |

- Walls and floors cost about twice step 4's for 4x the pixels: the writers' per-column
  and per-span work stays, the per-pixel work grows.
- `convert` grows about 2.7x: it now reads 30720 words where step 4 read 7680 and
  wrote each pixel 4 times. `slave` is the slave's other code, the writers'
  patches (`src/hires.s`) among it; the c2p is unchanged.
- The small view is now slower than full screen (as fast on the 68040 standing), which
  still draws 96x80: the writers still write colour words into the copper-slot layout, which
  `convert` then turns into pens. Step 7's own pen writers remove both the conversion and
  the word writes.

## Full screen at 288x240

Step 6 (plan, [internals](internals.md#the-1x1-renderer)), measured 26.11.2026 the same
way. The game's writers draw full screen at 288x240 into the lists (9x the original's
pixels), `_ds_one` converts it 1x1, and the c2p is the full screen one as before.

Frames a second and work a frame in ms (mean), against step 5's (full screen still the
96x80 one drawn 3x3, the same as step 4):

| CPU | View | Start | Walk |
|---|---|---|---|
| 68020 | full | 2.38 (413.5; step 5 5.56, 172.8) | 2.27 (435.0; 5.60, 169.4) |
| 68020 | small | 3.85 (250.4; 3.85, 245.5) | 3.77 (257.1; 3.85, 251.2) |
| 68030 | full | 7.14 (121.4; 16.67, 53.1) | 7.33 (127.4; 16.70, 52.3) |
| 68030 | small | 10.00 (84.7; 10.00, 82.9) | 10.68 (87.4; 10.73, 86.1) |
| 68040 | full | 7.14 (138.7; 12.50, 68.4) | 6.53 (145.9; 12.59, 67.7) |
| 68040 | small | 12.50 (73.5; 12.50, 72.7) | 11.54 (76.1; 11.66, 75.3) |

ms a frame standing at the start in full screen (MEASURED; gap shared by instructions in
brackets, DERIVED):

| CPU | walls + floors | convert | c2p | slave | objects |
|---|---|---|---|---|---|
| 68020 | 205.2 (206.1) | 77.7 (78.1) | 65.5 (65.9) | 36.6 (36.7) | 11.1 (11.2) |
| 68030 | 58.9 (59.7) | 21.9 (22.2) | 21.7 (22.1) | 10.1 (10.2) | 3.1 (3.2) |
| 68040 | 5.4 (60.6) | 0 (24.6) | 13.1 (38.7) | 1.1 (8.3) | 0.1 (3.0) |

- Walls and floors cost 1.8x the small view's for 2.25x the pixels; `convert` 2.25x, as
  its pixels. The c2p is the same as step 5's full screen.
- `slave` at 288x240 on the 68020: our sky 15.5 ms (`_t_sky`, 288 columns of 240 lines
  at most), the rest the writers' patches. In the small view the slave's share grew from
  step 5's 17.5 to 20.8 ms (68030 4.9 to 5.8): our sky (6.6 ms) in place of the game's,
  which cannot step a 1188-byte line. The frame rates are the same as step 5's.
- Full screen at 1x1 costs 2.4x (68020) and 2.3x (68030) its 3x3 frame; on the 68040 it
  is 2.0x, and as in step 5 nearly all of it is charged to gap ([What gap is](#what-gap-is)).

## The turn scene (step 7's start)

From step 7 on, measured with `tools/baseline.sh aprof MACHINE OUT turn` (WHD_ARGS=CUSTOM5=1),
26.11.2026, the build after step 6:
- **Setup:** one boot into level 1, keyboard control (K), then 30 fields on the up arrow
  to the middle of the start room.
- **Measured:** a full turn on the right arrow (`ab3d.py aprof turn`: until the angle at
  $61d78 has gone 8192) in the small view, then another in full screen.
- **Length:** the game turns by time, so a turn is about 120-140 fields on every CPU. On
  the 68020 in full screen that is only 6 frames.

Frames a second and work a frame in ms (mean, MEASURED):

| CPU | View | fps | work | walls | floors | convert | c2p | slave (sky) | objects |
|---|---|---|---|---|---|---|---|---|---|
| 68020 | full | 2.63 | 372.5 | 113.5 | 56.5 | 79.2 | 65.4 | 30.9 (20.7) | 10.6 |
| 68020 | small | 4.46 | 213.0 | 60.1 | 28.4 | 34.5 | 30.3 | 16.8 (7.3) | 9.1 |
| 68030 | full | 8.77 | 106.2 | 31.7 | 15.1 | 21.3 | 22.0 | 8.2 (4.6) | 2.8 |
| 68030 | small | 12.18 | 72.7 | 16.9 | 8.6 | 10.0 | 10.2 | 4.6 (1.9) | 2.4 |
| 68040 | full | 7.39 | 128.0 | | | | 13.0 | | |
| 68040 | small | 13.75 | 65.5 | | | | 5.0 | | |

- **68040:** 86-87% of its time is gap ([What gap is](#what-gap-is)), so only its frame
  rates and the c2p count.
- **Hottest code:** the wall strips `drawwallPACK0-2` and `simplewallPACK0-2`
  ($1ca80-$1cb6e), then the Gouraud floor spans `backbeforegour` and `acrossscrngour`
  ($20fd0, $20ff4).
- **Sky:** the turn shows more of it than the start does: 20.7 ms a frame on the 68020 in
  full screen.

### Pen bytes (the release build)

The game's writers write pen bytes in place of colour words
([internals](internals.md#pen-bytes); `BUILD=words` is the build before), so the convert
is gone. The same scene, 26.11.2026
(MEASURED; before line 0 was filled with black's pen in place of clearing it, the same 72
long writes a frame):

| CPU | View | fps | work | walls | floors | c2p | slave (sky) | objects |
|---|---|---|---|---|---|---|---|---|
| 68020 | full | 3.31 | 292.4 | 117.5 | 55.2 | 64.5 | 29.1 (17.5) | 10.6 |
| 68020 | small | 5.56 | 173.1 | 60.3 | 27.9 | 30.4 | 15.9 (7.7) | 9.1 |
| 68030 | full | 10.59 | 84.4 | 31.9 | 15.1 | 22.0 | 7.8 (4.7) | 2.8 |
| 68030 | small | 15.13 | 59.9 | 17.3 | 8.4 | 10.5 | 4.4 (1.9) | 2.4 |
| 68040 | full | 8.97 | 102.8 | | | 12.9 | | |
| 68040 | small | 15.68 | 54.7 | | | 5.0 | | |

- **Against the build after step 6:** the work a frame is 20-22% less in full screen and
  17-19% less in the small view on every CPU, about the convert's share (16-21%). The
  writers themselves cost what they did: a byte store takes as long as a word store.
- **Sampling:** keys turn by time, so each run sees the turn at different angles, and with 7
  or 8 frames a turn on the 68020 in full screen a routine's ms a frame moves by about 20%
  between runs of the same build (floors 44.5 and 55.2).
- **Now:** walls 38-40%, c2p 17-26%, floors 16-19%; on the 68040 still 83-84% gap.

### Step 7, change by change

The turn scene's work a frame in ms (mean, MEASURED), full screen / small view, after each
change (`tools/baseline.sh aprof MACHINE OUT turn`):

| Build | 68020 | 68030 | 68040 | What moved |
|---|---|---|---|---|
| Step 6 (`BUILD=words`) | 372.5 / 213.0 | 106.2 / 72.7 | 128.0 / 65.5 | |
| Pen bytes | 292.4 / 173.1 | 84.4 / 59.9 | 102.8 / 54.7 | the convert gone |
| The sky a line at a time | 275.1 / 171.2 | 81.2 / 58.6 | 102.0 / 54.1 | sky 17.5 to 8.1 ms (68020, full), 4.7 to 2.1 (68030) |
| Spans store with `(a3)+`; the gun's S pens at once | 268.5 / 167.3 | 81.0 / 57.7 | 100.9 / 53.2 | gun 5.0 to 2.6 ms, floors 50.9 to 47.2 (68020, full) |
| Our wall strip loops | 259.7 / 169.2 | 78.0 / 57.1 | 93.8 / 51.0 | strip loops' instructions 20% fewer, their time 8-12% less |
| No frame-flag wait | 262.6 / 166.9 | 78.2 / 55.5 | 93.0 / 49.5 | the same work; fps 13-25% more on the 68030 and 68040 |
| Full screen's c2p in one call (below the 68040) | 264.4 / 161.6 | 75.7 / 55.4 | 93.0 / 49.5 | c2p 64.6 to 59.2 ms (68020, full), 21.7 to 19.9 (68030); at FMODE 1 the 68040's was 13.1 to 17.5 |

- **The frame flag:** after showing a frame the game waited for its frame flag, which
  the copper sets at the top of each field ($32fe; not as the link's second player), so
  each frame took a whole number of fields: about half a field of waiting a frame (10.3 ms
  on the 68030 in full screen). `_p_show` already holds a switch until the screen it
  draws into is no longer shown, so the option skips that wait. The work is the same; the
  frame rates (fps, full screen / small view, MEASURED) went from 3.74 / 5.56 to 3.81 /
  6.00 on the 68020, 11.34 / 15.29 to 12.81 / 18.03 on the 68030 and 9.82 / 16.24 to
  10.78 / 20.25 on the 68040. A full turn on the keys still takes 121-135 fields: the
  game's speed follows time.
- **Full screen's c2p:** a call converts a run, so with rows of 36 bytes (FMODE 1) one call
  takes the frame: the 240 calls' set-up was 12-15% of the c2p's time. On the 68040 the
  c2p is Chip-bound, and FMODE 1's display takes twice FMODE 3's slots: 13.1 ms a frame
  became 17.5, so from the 68040 on the screen keeps 40-byte rows at FMODE 3. The small
  view's lines are 288 bytes for 192 pixels, so it still converts a row at a time.
- **Wall strips:** 8 pixels a pass at displacements, no `adda` or `dbf` a pixel: the
  instructions executed fall by a fifth, the time by 8-12% (68020 and 68030), since a pixel
  still reads a texel and a pen and writes one. The 68020's small view measured 1% slower
  over the turn, with floors 2 ms slower in the same run: the turn's angles (Sampling
  above).

Where it stopped (68030, full screen): our wall strip loops and the game's wall set-up
about 40% of the work, the c2p 26%, the floors 19%, objects 4%, geometry and logic the
rest. Every other routine of ours is under 1% (`_t_strip` 0.8%, `_t_split` 0.4%, the
floor steps 0.2% each), so the plan's step 7 is closed (§9).

On the 68040 FS-UAE counts instructions, not cycles (AmigaXDev's `measurement-method.md`):
a change that only moves memory traffic, such as a line stride whose columns spread over
the data cache's sets (`VASM_EXTRA=-DPSTRIDE=304`), measures nothing there; it measured
the same on the 68030 (84.5 / 59.1) and the 68040 (102.3 / 54.3). Not tried on hardware.

## Against the original (step 8)

The turn scene with the option off (`BUILD=original`, Psygore's slave: 96x80 in both views,
with its wait for the frame flag) and with it on, after step 7, in fps (MEASURED,
27.11.2026). The 28 MHz 68020 is the a1200-fast with `--uae_cpu_frequency=28375160`
(`baseline.sh` machine `a1200-28`, an ACA1221-class accelerator):

| CPU | Original | Small view | Full screen | Ours' work a frame, small / full (ms) |
|---|---|---|---|---|
| 68020 14 MHz | 12.50 | 6.20 | 3.79 | 161.6 / 264.4 |
| 68020 28 MHz | 19.42 | 11.16 | 7.72 | 89.8 / 129.7 |
| 68030 50 MHz | 23.31 | 18.07 | 13.22 | 55.4 / 75.7 |
| 68040 25 MHz | 26.47 | 20.17 | 10.78 | 49.5 / 93.0 |

The original's work a frame is 72 / 45 / 33-35 / 26 ms on the four. A 28 MHz 68020 draws the
small view at more than half the original's rate and full screen at 40%; the 14 MHz one
at half and 30%.

## The dark room fight

Level 1's dark room with the aliens, in full screen, measured 28.11.2026 on the 68030
aprof machine with the release build (`WHD_ARGS='CUSTOM1=1 CUSTOM5=1'`, unlimited energy):
`ab3d.py play door` from the level's start (through the first door into the room's
middle), then `ab3d.py aprof 250 OUT turn720` (two full turns on the mouse firing, then 40
fields firing). The shots hit the aliens and set off a barrel on the second turn.

| | fps | work a frame, mean / p50 / p95 (ms) |
|---|---|---|
| Dark room fight | 10.41 | 96.2 / 100.2 / 140.2 |
| The turn scene (start room, step 8) | 13.22 | 75.7 |

ms a frame (mean, MEASURED):

| Walls | Floors | c2p | Objects | Sky | Geometry | Logic |
|---|---|---|---|---|---|---|
| 30.4 | 20.9 | 19.3 | 11.3 | 2.1 | 3.1 | 2.9 |

- **Walls:** our strip loops `_t_wdraw` 17.0 ms and `_t_wsimple` 4.9 ms, plus the game's
  set-up 8.3 ms (`pastscrinto`, `CalcAndDraw`).
- **Floors:** the Gouraud spans `backbeforegour` and `acrossscrngour` take most of them.
- **The slowest frames (7 fields, 138 ms):** they look back through the door into the lit
  corridor, once a turn. Floors then take 43-49 ms and walls 13-15 ms of the game's set-up.
- **Objects:** 4 ms a frame facing away from the aliens, 18-25 ms with the aliens in view
  and the explosion. 25 ms is the explosion frame.
- **The c2p:** the same 19-20 ms in every frame (288x240).

## Not measured

- A barrel shot point-blank. The dark room's barrels stand at the far ends of its side
  aisles. The starts of levels 2-6 (reached with CUSTOM1=4 and F1) had nothing heavier
  than level 1's start corridor.
- A real 68030 or 68040, and the a1200 without fast memory (it cannot run the game).
