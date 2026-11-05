# Powerdrome internals

Current release status and validation limits are in [open work](open-work.md).

## Current measurements

Fine mouse rotation uses Q12 angular rates and a private Q28 matrix, publishing
native Q14 orientation every 20 ms. The original calibration gain and 90 ms control
input cadence remain. See [timing design](timing-implementation.md#fine-mouse-rotation).
Current uninstrumented 500-field Practice measurements are:

| Configuration | Intervals / fields | FPS | Mean ms/frame |
| --- | ---: | ---: | ---: |
| A1200 + fast, NoCache, coarse mouse control | 240 / 494 | 24.291 | 41.167 |
| A1200 + fast, NoCache, fine mouse | 238 / 494 | 24.089 | 41.513 |
| 060/50 + fast, NoCache, fine mouse | 455 / 499 | 45.591 | 21.934 |
| 060/50 + fast, CACHE, fine mouse | 490 / 499 | 49.098 | 20.367 |

The A1200 comparison changes only `TIMING_MOUSE`, and uses matching hunk placement.
Fine mouse costs 0.833% route throughput there. These are end-to-end routes, not
isolated rotation costs. Evidence: `tmp/mouse-steering/perf*/`.

### Release baseline matrix

These measurements precede the single-checkbox UI and fine mouse-steering changes.
They are historical release baselines, not performance measurements of the current
mouse integration. Enhanced and native paths are now selected by `CUSTOM1=1` and the unchecked default.
They are FS-UAE PAL route measurements over 500 fields from the first driving
presentation (`$bc7c`), counted with read-only breakpoints. FPS uses complete
first-to-last presentation intervals. Builds have no phase instrumentation or
renderer twins during these measurements; VERIFY/coverage supply native inputs.
The reference uses the same modern loader with native timing and rendering.
Timing changes also change motion and scene inputs, so these are end-to-end route
comparisons, not identical-scene renderer speedups or physical-board predictions.

| Machine | WHDLoad | Route | Native intervals/fields | Release intervals/fields | Native → release fps | Release ms/frame |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| M1 | NoCache | Practice | 104/456 | 104/456 | 11.404 → 11.404 | 87.69 |
| M1 | NoCache | Race | 113/492 | 113/492 | 11.484 → 11.484 | 87.08 |
| M2 | NoCache | Practice | 106/468 | 106/468 | 11.325 → 11.325 | 88.30 |
| M2 | NoCache | Race | 114/495 | 114/495 | 11.515 → 11.515 | 86.84 |
| M3 | NoCache | Practice | 153/496 | 153/497 | 15.423 → 15.392* | 64.97 |
| M3 | NoCache | Race | 162/495 | 162/495 | 16.364 → 16.364 | 61.11 |
| M4 | NoCache | Practice | 154/491 | 240/494 | 15.682 → 24.291 | 41.17 |
| M4 | NoCache | Race | 166/495 | 266/496 | 16.768 → 26.815 | 37.29 |
| M5 | CACHE | Practice | 194/496 | 389/499 | 19.556 → 38.978 | 25.66 |
| M5 | CACHE | Race | 212/497 | 424/496 | 21.328 → 42.742 | 23.40 |
| M5 | NoCache | Practice | 194/496 | 389/499 | 19.556 → 38.978 | 25.66 |
| M5 | NoCache | Race | 212/497 | 424/496 | 21.328 → 42.742 | 23.40 |
| M6 | CACHE | Practice | 368/498 | 490/499 | 36.948 → 49.098 | 20.37 |
| M6 | CACHE | Race | 325/497 | 499/499 | 32.696 → 50.000 | 20.00 |
| M6 | NoCache | Practice | 178/497 | 452/499 | 17.907 → 45.291 | 22.08 |
| M6 | NoCache | Race | 198/496 | 461/499 | 19.960 → 46.192 | 21.65 |
| M7 | CACHE | Practice | 404/499 | 490/499 | 40.481 → 49.098 | 20.37 |
| M7 | CACHE | Race | 333/499 | 498/499 | 33.367 → 49.900 | 20.04 |
| M7 | NoCache | Practice | 178/497 | 457/499 | 17.907 → 45.792 | 21.84 |
| M7 | NoCache | Race | 199/497 | 465/498 | 20.020 → 46.687 | 21.42 |

*The user accepted M3 Practice's specific 0.201207% shortfall: 153/497 versus
153/496. A fresh retry reproduces the entire field sequence exactly. This remains
an exception, not a strict pass or a general tolerance. The other 19 comparisons
meet the strict gate. Machine/memory, emulator and ROM settings match their native
references. Evidence is under `tmp/phase-f/fast-required/`; native references remain
under `tmp/phase-b/`.

### Measured machine configurations

| ID | CPU and model | Chip / fast / slow memory | Requested frequency |
| --- | --- | --- | --- |
| M1 | A500, 68000 | 512 KiB / 0 / 1,536 KiB | Model default |
| M2 | A500, 68000 | 512 KiB / 4 MiB / 1,536 KiB | Model default |
| M3 | A1200, 68EC020 | 2 MiB / 0 / 0 | Model default |
| M4 | A1200, 68EC020 | 2 MiB / 4 MiB / 0 | Model default |
| M5 | A1200, 68030 | 2 MiB / 4 MiB / 0 | 25 MHz |
| M6 | A1200, 68040-NOMMU | 2 MiB / 4 MiB / 0 | 25 MHz |
| M7 | A1200, 68060-NOMMU | 2 MiB / 4 MiB / 0 | 50 MHz |

All runs use PAL and no host input. M5–M7 request real-speed cycle-exact execution,
zero CPU multiplier and the listed frequency. CACHE/NoCache labels are WHDLoad
options. The emulator's non-MMU 040/060 paths do not certify physical cache behavior.
The machine settings are executable in `tools/release_matrix.py`.

## Rendering costs and retained choices

The renderer stages native planar graphics in fast RAM and publishes 21,600 bytes
to chip RAM after the display handshake. The four plane bases, 760-byte copy offset
and 8,000-byte stride are longword-aligned. Ten-register MOVEM blocks copy 40 bytes
at a time. HUD writes extend outside the staged rows 19–153 and use the blitter,
so the HUD stays native. No MOVE16 or cache-policy change is applied.

Moving the handshake after fast-memory drawing lets rendering overlap the previous
display interval. Development measurements increased Practice throughput from
21.881 to 24.040 fps on 020/fast, 31.552 to 38.277 on 030, and 41.984/42.886 to
44.389/44.890 on uncached 040/060. Separate beam checks covered 308 copies: every
copy followed the completed wait in a VBL later than the preceding presentation.
The early wait remains for native drawing and twin references.

All installed static polygon code also serves fallback scenes with native bitmap
pointers. A 200-field 020 departure trace observes zero game-code writes, versus
313 writes to each native branch displacement in its reference. Pit and title
images match; 020/030/060 twins passed. This routing is a correctness choice as
well as a small throughput gain. See [renderer design](performance-implementation.md)
and [cache limitations](accelerator-cache-testing.md).

The guest phase timer's attribution agrees with 020 instruction tracing within
0.00571% across 46 complete shared intervals. The development baseline on uncached
040/060 spends about 13.62/13.31 ms in rendering, 3.18 ms copying and 1.94/1.93 ms
in HUD work per Practice presentation. With CACHE, rendering costs 8.37/7.92 ms,
copy 3.19 ms and HUD 1.42/1.37 ms. These are baseline phase costs before the later
wait-overlap optimization, not a phase profile of the final release. Presentation
including LoadView costs about 0.11 ms, below 1% of a frame. Near 50 fps, wait time
also paces the display and is not entirely recoverable performance.

## A500 and chip-only limits

The retained A500 path uses original rendering and timing. The original track
profile spends 54.27% of recorded CPU cycles in polygon edge/span work and 8.45%
in background fill; WaitBlit is only 0.17% on track but 47.05% in the pit.
See [the departure profile](practice-profile.md) for exact windows and boundaries.

A pipelined blitter clear trial measured 104/494 (10.526 fps), versus native
104/456 (11.404 fps). Completed traced frame cost rose from 641,039 to 665,937
cycles. The required earlier display wait consumed most of the removed clear
cost; polling and setup added work. The rejected trial is absent from production.

No individual measured OS/VBL call met the 3% optimization threshold. BltBitMap
was largest at 2.580% of the original track window; LoadView was 0.186%.
Static dispatch setup costs only 0.181%, an upper bound too small to justify an
A500 chip-code rewrite. The aggregate 9.6% Kickstart share is not one replaceable
call. Native A500 simulation deltas on the measured route exceed the old minimum;
changing that clamp alone cannot improve its frame rate.

A full-timing stock A1200 trial with static raster code in chip RAM measured
139/495 (14.040 fps), below its native-raster control's 144/494 (14.575 fps).
That experiment was removed. Stock A1200 now retains original timing as well as
rendering. Its accepted release comparison is listed in the release results.

The original and modern loaders are not timing-identical. Performance comparisons
use the same modern loader, while the original slave reconstruction remains
byte-identical to the supplied reference. Measurements are emulator evidence;
they do not predict physical accelerator-board gains.

## Inputs and loader

Supported input: PAL original, Retroplay `Powerdrome_v1.0_0140.lha`, Galahad/Fairlight slave 1.0 (22 May 2003).
Both supplied archives contain the same 1,592-byte slave; neither contains source.
`whdload/original/Powerdrome.s` reconstructs it and rebuilds byte-identically with vasm.

The header declares WHDLoad interface 15, flags `NoError|EmulPriv`, BaseMem `$80000`,
ExpMem `$40000`, loader `$132`, F10 exit (`$59`), and no CUSTOM options.
It is an OS game: the old slave loads Kickstart 1.3 through `resload_LoadKick`, patches it,
and boots an OFS disk image. Expansion memory is entirely the Kickstart image; the game
and OS live in 512 KB chip RAM. Disk startup is `loadwb` then `endcli >nil:`.

The LoadSeg callback at slave `$142` identifies `endcli`; its hunk offset `$4` starts with
`movea.l $164(a2),a4` (`286a0164`). The slave replaces six bytes with a jump to slave `$18c`,
which opens dos.library and loads `Powerdrome:PD`. It searches PD for `2f0e4dfa` and replaces
six bytes at game `$843c` with a jump to slave `$1ca`. This returns Copylock value `$766cc95c`;
the legacy registered-user check precedes it. No renderer or simulation patches exist.

`pd` is 111,072 bytes. It has one CODE hunk, file offset `$20`, length `$18548` (99,656 bytes),
followed by HUNK_RELOC32 (2,841 relocations to hunk 0) and HUNK_END. Code and mutable data share
this hunk. Entry jumps to game `$4fc0`. It is predominantly assembly with absolute relocated
references, so routine names use static and observed call targets rather than C prologues.

## Original Kickstart patches

These offsets are relative to the Kickstart image; targets are slave-hunk offsets.
The patch list starts at slave `$254`. It adapts memory/Exec, graphics, trackdisk reads and
writes, disk changes and LoadSeg. No source-level meanings are inferred beyond the decoded list.

| Kickstart offset | Patch | Argument |
|---|---|---|
| `$00132` | `W` | `0000` |
| `$0061a` | `P` | `slave:0326` |
| `$00592` | `P` | `slave:032a` |
| `$0025a` | `W` | `0000` |
| `$00546` | `P` | `slave:0332` |
| `$01354` | `P` | `slave:0338` |
| `$015b2` | `PS` | `slave:0342` |
| `$014b6` | `PS` | `slave:035a` |
| `$00422` | `PS` | `slave:036a` |
| `$03012` | `I` | `` |
| `$004f4` | `L` | `ffffffff` |
| `$04cce` | `S` | `0x4` |
| `$06d70` | `PS` | `slave:039e` |
| `$06d86` | `PS` | `slave:03b6` |
| `$0ad5e` | `PS` | `slave:03d6` |
| `$0aecc` | `S` | `0x18` |
| `$0af96` | `P` | `slave:03c0` |
| `$0b00c` | `P` | `slave:03c4` |
| `$0d5be` | `PS` | `slave:03f4` |
| `$2a3b4` | `P` | `slave:0428` |
| `$2a5d8` | `I` | `` |
| `$2a0e2` | `P` | `slave:04d8` |
| `$29cfa` | `P` | `slave:0428` |
| `$2a6d6` | `PS` | `slave:04e4` |
| `$2af68` | `I` | `` |
| `$2af6e` | `I` | `` |
| `$2a19c` | `I` | `` |
| `$2960c` | `P` | `slave:0516` |
| `$04984` | `P` | `slave:0418` |
| `$33ef0` | `PS` | `slave:05ae` |
| `$3c9b6` | `PS` | `slave:05b6` |
| `$36e4c` | `PS` | `slave:056e` |

## Display and timing

- Game `$5684` is the installed VBL server. It samples mouse/input state, increments the long
  at game `$48fe`, and sets `a6+$494` as a VBL handshake. The main state base is game `$a6e`.
- Game `$59b6` reads CIA-A TOD high/middle/low, differences the prior sample at game `$f9a`,
  multiplies the delta by four and adds it to the clock at game `$f96`. This is called from
  the VBL server every fourth field and from main code. Other code can adjust this clock.
- Game `$7f7a` updates the clock, differences the previous frame timestamp (`a6+$218`), clamps
  that delta to 8..50 and stores the word at `a6+$21c`. It then exchanges bitmap pointers.
  Physics reads this word at `$ccf2` and `$d56c`; a constant-step model would be incorrect.
- Game `$8056` calls `$7f7a`, calls graphics.library LoadView and clears the VBL handshake.
  Multiple non-racing paths call it. Normal driving is counted at its caller `$bc7c`;
  departure animations are excluded from driving FPS.
- The renderer waits for the VBL handshake at game `$112a6`.
- The menu's idle timeout at `$12ec6` compares elapsed clock units with 18,000 and returns
  12,345 to its caller. This enters the recorded title demo, not a race.
- RNG seeding at `$11db4` mixes the clock into `a6+$62`, then pilot-name words are XORed in.
  The native title route repeats without a seed override; racing RNG ownership
  on the enhanced path is covered by the timing equivalence checks.

The Practice trace now confirms the normal loop's order: `$ca3e` updates movement, calls the
scene renderer at `$cee8`, runs post-render gameplay/HUD work, then the caller presents through
`$bc7c`/`$8056`. There are 70 player movement updates and 70 renderer entries; the 69 completed
iterations each reach the native delta calculation. All 68 adjacent sampled presentations have
raw delta equal to four times their PAL-field separation. Observed deltas are 12–32, without
clamping. Simulation is coupled to rendering but its main displacement uses elapsed time.
This describes the original game. See the [timing design](timing-implementation.md)
for the enhanced scheduler and the [renderer design](performance-implementation.md)
for fast planar staging.

The normal build includes `TIMING_FULL`, separating those native frame duties into
logical 20/90 ms updates on 68020+ with real fast RAM. It uses the continuous opponent
clock for repair starts and expiry (`$d4b6/$d4fe`), eliminating a sampled-clock
threshold difference found during endurance. Focused comparison and the corrected
600-second pair pass: 30,001 common world/RNG states and 6,666 control/input/fuel
updates match exactly, with zero endpoint debt. Natural-weather validation
is deferred by the user after a ten-minute retry without a weather episode; expiry
and restoration remain untested; see the [current gate ledger](open-work.md#phase-e-gate-ledger).

## Development slave and reproducible title-demo profile

`whdload/Powerdrome.s` uses unmodified WHDLoad 20 KickEmu sources, interface 17, one disk,
512 KiB chip for the guest, 256 KiB expansion for Kickstart and 128 KiB additional guest
expansion. It retains the EndCLI redirection and Copylock replacement, with a signature
check at game `$843c`. Cache selection is left to standard WHDLoad options. `CUSTOM1=1` enables fast planar rendering and timing together on 68020+ with real fast RAM;
the unchecked default keeps both paths original. See the [implementation report](performance-implementation.md). In VERIFY builds only, CUSTOM5 replaces the name-entry key-ready
and key-read calls at `$13772` and `$1377c` with ready/Return responses. The shipped original
and byte-identical rebuild both reach the name screen; the fixture-enabled modern rebase boots
through it into the automatic title demo. The [loader audit](loader-equivalence.md) resolves
the original's legacy registration value in D2: the successful caller overwrites it before use. Matched 68000/68020 startup/Practice
captures agree after explicit allocation and timing allowances. OS execution and departure
timing are not identical; performance comparisons must use the same loader.

The title demo's `$107d6` advances a recorded camera index (`a6+$292`) by its step
(`a6+$294`, initially 2) per rendered frame. It calls the shared 3D renderer and moves an
inset across the title background. `$1067e` is its post-render display-update call and the
capture anchor. This demo therefore plays faster when rendering is faster, independently
of the separate clock-delta-based racing motion; do not conflate the two timing models.

Fixed title-demo windows at revision `02dbc27` use the development VERIFY slave with CUSTOM5=1, PAL, WHDLoad 20.0
and 100 fields. Two fresh A500 boots have identical initial chip RAM, CPU instruction records
and DMA records throughout. Every image matches except the three rightmost host-border columns,
which the comparator excludes. An independent read-only breakpoint counter exactly reproduces
both machines' complete per-field frame patterns.

| Machine | Frame intervals / PAL fields | Demo fps |
|---|---:|---:|
| 68000, 512 KB chip, 1,536 KB slow, no fast | 18 / 93 | 9.7 |
| A1200, 68EC020, 2 MB chip, 4 MB fast, no slow | 25 / 95 | 13.2 |

The second machine still runs the game in chip RAM; fast RAM holds KickEmu and host support.
These are demo drawing rates, not racing baselines or a performance improvement.

On the A500, the trace records 100 game VBL callbacks and 408 level-3 entries. DMA slots: 31.2% free,
27.1% CPU, 17.2% blitter, 22.5% bitplanes (remainder refresh/copper).
Self attribution: game `$10df2` 21.8%, `$15ee8` 20.8%, `$1609c` 7.0%; verify boundaries with
instruction hotspots before selecting a replacement. KickEmu's complete WaitBlit routine
uses about 23.1% of recorded cycles, including its CIA delay reads. A detector counting only
busy-bit tests and branches substantially undercounts that wait. STOP instruction records
account for about 6.35% of cycles. These are recorded emulator costs, not hardware measurements.

On the 68020, complete WaitBlit accounts for 31.9% of recorded cycles and STOP records 11.6%.
DMA slots: 32.1% free, 20.0% CPU, 23.4% blitter, 22.5% bitplanes. There are 100 game VBL
callbacks and 100 level-3 entries. The trace cycle scale doubles with this CPU backend; do not
compare raw cycle totals across CPUs as elapsed PAL time. FPS comes from field counts.

## Practice input route and movement anchor

VERIFY `CUSTOM5=2` uses the same Enter hook as the title route, then replaces the native
menu key-ready/read JSRs at `$12f6a` / `$130a4` with one `3` keypress. The game's rectangle
table at `$432c` maps item 3 to the top-middle button; its normal dispatcher at `$1207a`
selects Practice. At the pit, `$13c50` / `$13cde` receive one Space keypress. Each hook covers
one complete six-byte JSR; no static branch enters an overwritten instruction's interior.
No input fixture is present in the normal build.

After accepting Space, the native code performs its stationary departure delay, then calls
`$1475c`. The first loop iteration at `$14764` is the capture anchor: it draws the ship at
successive vertical coordinates from `$144cc` (51, 50, 50, 45, ...), moving out of the pit.
The later `$1020e` routine handles the cockpit departure path. A capture starting at `$14764`
includes the visible pit launch, the screen transition and subsequent cockpit gameplay.

The A500 practice-launch capture has 500 consecutive PAL fields and 500 game VBL callbacks,
71,050,998 recorded CPU cycles, and 6,205,664 instruction records (all have PCs). Its first
100 fields match the short-cap reference's initial chip memory and CPU/DMA records exactly,
validating that lifting the host profiler command cap does not alter that portion of gameplay.
The [phase-specific practice profile](practice-profile.md) identifies CPU polygon rasterization
as the track bottleneck: edge/span work takes 54.27% of track cycles, background filling 8.45%.
Complete WaitBlit takes 47.05% in the pit but only 0.17% on track. These use verified,
disjoint instruction ranges; the generic report's inferred `$159e8` routine label incorrectly
absorbs branch-entered span writers. See the profile for exact boundaries and limitations.
