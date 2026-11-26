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

## Not measured

- The heaviest scene. The level 1 route and the starts of levels 2-6 (reached with
  CUSTOM1=4 and F1) had nothing heavier than level 1's start corridor, so the baseline has
  two scenes. A later step may add a saved position with many aliens.
- A real 68030 or 68040, and the a1200 without fast memory (it cannot run the game).
