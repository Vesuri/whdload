# The enhanced slave

`src/Indianapolis500_WHD.s` is StingRay's v3.0 slave plus one fix that is always on (the audio
DMA wait, below) and optional patches in `src/Indianapolis500_*.s`. With the option off, every
optional range holds the original bytes (`tools/check_disabled.py`). How the original works:
[game.md](game.md). How to build, run and measure: [profiling.md](profiling.md).

## Options

| Tooltype | Splash window | Effect |
|---|---|---|
| `Custom1=1` | "High frame rate support (68020+ with Fast RAM)"; off without the tooltype, on in the installed icon (the release installer writes `CUSTOM1=1`; `CUSTOM1=0` restores the original) | Motion and CPU drawing, only on a 68020 or better with hunk 0 in fast RAM (not chip RAM below `$200000`, not slow RAM at `$C00000–$DFFFFF`). Elsewhere it is ignored, because both features would slow the machine down |
| `Custom1=4/5/6/7` | not listed (tooling) | Bit 2 = manual: bits 0 (motion) and 1 (CPU drawing) are applied on any machine. 4 = all off |
| `Custom3=N` | not listed (VERIFY builds) | Pixel-twin fixture: 0 natural demo, 1–6 director 50/200/350/500/650/800 |

The slave does not manage caches. StingRay's `Enable_Cache` marks BaseMem non-cacheable, and
without the MMU WHDLoad then turns every cache off. Users should pass WHDLoad's `DCache` (or at
least `Cache`), which matters a lot on a 68030 (see results). The release readme should say so.

**WHDLoad 17 or newer.** `ws_Version` is 17 because of `ws_config`, the splash-window
options. Everything else needs older versions: tags v7, `resload_*` v10, patch commands up to
`PL_PSS` (v16). Do not add v18+ functions, patch commands or header fields without raising
`ws_Version` deliberately. Builds against the WHDLoad 19.2 and 20.0 includes are byte-identical,
and the slave runs under 19.2 and 20.0. No WHDLoad 17 or 18 binary has been tried.

`Select_Performance` decides which features apply. `Apply_Enhancements` applies the patch lists
after the game is loaded.

## Features

**Audio DMA wait (always on, `Audio_DMA_Wait`).** The music player (`intro:102de`, reached
through the `$fe00` hook in the intro and the game's menus) and the sound effects (`game:a384`)
turn audio DMA off, set up the channels, then wait with 401 reads of address 0 before turning
DMA back on. That is about 16 raster lines on a 68000, but 0.9 lines measured on the 68040
(FS-UAE `a1200-040`, MMU on, `DCACHE`). The channels are still playing when DMA comes back on,
so the new notes do not restart and the intro music sounds unsteady. `PL_PSS $629e` (intro)
and `PL_P $a384` (game) wait for nine raster-line changes instead: at least 8 whole lines, about
0.5 ms. With DMA off, a channel finishes the period it is in and then plays the low byte for
one more period, using the period just written, before it goes idle. The longest period the
game uses is 794 colour clocks (the effect at `game:a1ac`; music notes reach about 260, the
noise drums 672), so the worst case is 1,588 colour clocks, 7 lines. Five line changes
(one period) still left 8 failed drum restarts. In a race the wait runs about three times a
second (31 and 33 calls in two 500-field windows, 68040 race build), about 0.15% of the time.
Afterwards d1.w = −1 and a0 = 0, as with the loop.

Verified in FS-UAE with its own workaround off (`--uae_chipset_hacks=8`; profiling.md). The
emulator logs every DMA-on that finds the channel still playing. Over about 40 s of intro on
the `a1200-040` with `CUSTOM1=1 DCACHE`: 68 with the original slave (channels 0 and 3, all at
`intro:102f6`), 8 with a five-line wait, 0 with nine lines; 0 for the original slave on the
A500. Audio recordings aligned with an A500 recording by onset cross-correlation: the
nine-line build matches it as closely as a second A500 run does (21 of 87 onsets unmatched
against 21 of 89, no drift between 3-second windows); the original slave on the 68040 leaves
56 of 100 unmatched and drifts by up to 0.12 s.

**Motion (`PL_MOTION`, `Indianapolis500_Motion.s`).**
- `PL_PSS $152` (`motion_wait`) removes the main loop's wait for a simulation tick, except during
  the replay transition wipe, which advances one step per pass and keeps the original pace.
- `PL_PS $9c06` keeps a private CIA tick count.
- `PL_P $3af0` replaces SOFT's common exit and records `prev`/`cur` snapshots: the 9 camera
  words, the track position, the mode bytes, the viewer, the camera source and each car's pose,
  plus a CIA timestamp. The poses are those the frame will draw: the car records' `+6/+8/+10`
  in the cockpit, the external view's nodes `+16/+18/+20` in the demo and replays (game.md).
  Replays move only the nodes, and in the demo the nodes trail the records by a tick.
- Each frame, a hook rewrites only the renderer's copies: `PL_PSS $26d4c` for demo and external
  cameras, `PL_PS $270` for the cockpit. α is the time since the last SOFT exit divided by
  4 CIA ticks (Q14). Coordinates are linear, angles take the shortest arc, track positions wrap
  at 39 600, and each car's native distance bias is kept.
- **Demo and replays interpolate:** `prev + (cur − prev) × α`. That is smooth and exact but
  shows the scene one simulation tick (67 ms) late, which only matters when driving.
- **Driving (cockpit snapshots):** the camera and the player's car extrapolate,
  `cur + (cur − prev) × α` with α from 1 to 2. That removes the delay, but sudden changes (wall
  hits, hard braking, steering reversals) overshoot for up to one tick. Opponents move from
  `cur` towards `next` with α − 1: `motion_predict_cars` computes `next` at each SOFT exit with
  the field loop's own equations (game.md). That pose is exact, so opponents neither lag nor
  jump. A car that did not reach the previous prediction (contacts, cars the field loop does
  not move) is extrapolated for that tick.
- It snaps (α = 1) at camera cuts, at source changes between cockpit and external, and at
  teleports (more than 1000 units). When SOFT has not run for more than four CIA ticks (pause,
  menus), the latest tick is shown. During the replay transition wipe (view style 2) the CIA
  handler requests no SOFT and skips the motion clock, so the hook leaves those frames alone.
- Input is still sampled once per tick, and the simulation is untouched. The original SOFT
  trigger is kept.

**CPU drawing (`PL_SPANS`, `Indianapolis500_Spans.s`, `_Colour.s`, `_Line.s`, `_Clear.s`).**
- Spans: `PL_PSS $bbb4/$bcbc/$be04` replace the prepared span loops. Solid spans use one of
  sixteen binary-palette routines, with the exact general minterm for other colour words. Dither
  keeps the caller's phase. Narrow (one- or two-word) textured rows are drawn by the CPU. Wider
  textured rows are batched as one four-plane blit (`span_texture_batch`), with the modulos
  computed before the BBUSY wait.
- Lines: `PL_P $b92c` (`line_cpu`) replaces the four line-mode blits per line. It follows
  WinUAE's line stepping exactly, merges dots per word into one four-plane read-modify-write, and
  stores the native `game:e842/e832/e852` copies. Colour words other than 0/`$FFFF` fall back to
  the native blits.
- Background: the final wait of `game:0c0ba` becomes asynchronous (`PL_PSS $c29a`). Barriers
  sit at the first later blitter or bitmap access: `bb8e`, `bc96`, `bde4`, `b8ca`, `b574`.
  `PL_P $c240` fills planes 0 and 1 with 32-bit CPU stores instead of two `$01FF` blits.

**Hooks** must cover whole instructions with no direct branches into them
(`tools/audit_hooks.py`). Indirect entries need executed-path evidence. `PL_PSS …,2` is needed
where the replaced code is eight bytes.

## Verification

- **Pixel twins** (VERIFY build, `Indianapolis500_PixelVerify.s`): each span, line and
  background operation runs the new code into a guarded shadow bitmap, then the native code into
  the real one. All four
  planes and the surviving registers, including X, are compared. Run the prepared loop, not the
  whole function: dither callers enter with their own phase.
- **Motion check** (`motion_frames.py`): captures the renderer's native inputs before the hook and
  checks every rewritten word against the formula. It also checks that the native car poses
  equal the latest snapshot, which is how recording the wrong state shows (the replay bug).
- **Gameplay state** (`state_fields.py`, `compare_state.py`, `compare_soft_writes.py`): per-SOFT
  snapshots, aligned by simulation tick, never by frame.
- **Disabled check** (`check_disabled.py`): with the option off, every optional range is the
  original.

Evidence so far:
- 1,000 pixel-twin frames at each demo fixture for the span code: 234,066 comparisons, zero
  differences.
- 200 frames per fixture for the line drawer and the background planes 0/1.
- 1,000 frames of actual race driving: 17,719 comparisons.
- Gameplay state equal to the original over 1,000+ demo ticks with the tick wait removed and
  motion on (68000, 68020).
- 1,010 race ticks equal between two feature builds. The current build has not been compared
  against the original yet (open-work.md).
- 100-frame motion checks of the current build, 68040/25 cycle-exact, `CUSTOM1=1 CACHE DCACHE`:
  - Race, cockpit: 0 differences; all 800 visible opponent poses predicted; 0 of 800 native car
    poses differ from the snapshot.
  - Demo: 0 differences, interpolated; 0 of 1,406 native car poses differ from the snapshot.
  - Instant replay (the `DRIVING_REPLAY` fixture): 0 differences; 949 of 949 poses moving and
    matching the native ones. The build before the fix showed 0 of 800 moving and all 800
    different, the reported frozen cars.
- With the option off, all 17 optional ranges hold the original bytes (`check_disabled.py`).
- Option off against v3.0, 1,010 demo SOFT snapshots on the 68040/25 (`CACHE DCACHE`): hunk 0 and
  BSS hunk 5 are identical tick for tick to the shipped v3.0 slave padded to the same size
  (an ad hoc comparison of `fixed_window.sh` state captures). Only the six jumps into the slave differ (the audio DMA wait, added later, makes a seventh at `game:a384`), plus renderer workspace
  (hunk 1, one hunk-0 snapshot at `game:0e81d…`) and one stack byte, all mid-frame timing.
  The bigger slave makes WHDLoad load the game `$2000` lower, and the demo's course depends on
  the load address: the shipped and the padded v3.0 diverge at tick 816 exactly as ours does.
- The replay transition wipe (the first one after the fixture's request, ticks 1212–1274):
  62 CIA ticks with the option on and with it off. With the tick wait simply removed, before
  `motion_wait`, it took 1 tick.
- A race window with predicted opponents against plain extrapolation (784 opponent frame triples). The largest
  frame-to-frame change of displayed velocity fell from 2.5 to 1.2 along the track, from 19 to
  7.5 sideways, and from 133 to 33 in heading (units per CIA tick). The rest is real rate
  changes and integer rounding.

## Results

Measured with `SWAP_ONLY`, 100 fields per window, cycle-exact; fps per demo window. Later builds
changed only the presentation, not the drawing.

| Machine | WHDLoad options | opening | 50 | 200 | 350 | 500 | 650 | 800 |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| A500 (68000, 512K chip + 1.5M slow) | `Custom1=1` | 5.1 | 4.3 | 3.6 | 5.9 | 7.6 | 7.4 | 3.9 |
| Stock A1200 (68EC020/14, chip only) | `Custom1=1` | 7.4 | 6.3 | 5.2 | 9.1 | 11.1 | 10.8 | 5.8 |
| Stock A1200 | `Custom1=1 DCache` | 10.1 | 8.7 | 7.1 | 11.2 | 13.5 | 13.4 | 8.0 |
| 68EC020/14 + 4M fast | `Custom1=1` | 14.3 | 12.2 | 10.0 | 16.7 | 21.4 | 18.4 | 11.6 |
| 68EC020/14 + 4M fast | `Custom1=1 DCache` | 15.3 | 14.9 | 12.2 | 18.6 | 24.0 | 20.9 | 12.0 |
| 68030/25 + 4M fast | original | 15.2 | 14.9 | 15.1 | 14.9 | 14.9 | 15.1 | 15.3 |
| 68030/25 + 4M fast | `Custom1=1` | 25.8 | 22.2 | 16.7 | 30.6 | 44.4 | 34.8 | 21.9 |
| 68030/25 + 4M fast | `Custom1=1 DCache` | 25.8 | 25.0 | 24.5 | 39.4 | 48.0 | 50.0 | 23.0 |
| 68040/25 + 4M fast (code before the background fill) | `Custom1=7` | 25.8 | 25.3 | 25.0 | 39.4 | 48.0 | 50.0 | 25.0 |

- The A500 and stock A1200 rows equal the original game, because the toggle is ignored there.
  Forced on, both features cost 10–20% on the 68000. On a chip-only 68020 the whole gain is the
  instruction cache.
- **Race driving** (cockpit, A1200 68040/25, `CACHE DCACHE`): 14.9 fps original, 33.2 fps with
  `Custom1=1`.
- On the 68030/25 the heaviest frames take 36–40 ms from `game:26d4c` to `game:0b574`, before the
  HUD and SOFT. A steady 25 fps would need 3–4 ms off the worst frames.
- **Limits.** The heavy views are bound by chip RAM and the blitter. A 68040 at 25 or 40 MHz
  gives the same 25.0 fps there, because chip accesses do not get faster with the CPU. 50 fps in
  those views would need less chip work per frame: for example, drawing the 3D view into a
  fast-RAM buffer and copying it to chip once per frame. That is unmeasured, and FS-UAE's
  68040/060 chip timing is approximate.

## Tried and rejected

Do not revisit without new evidence. 68030/25 fps unless noted.

| Idea | Result |
|---|---|
| All wide textured rows by CPU | Slower (200: 24.0 → 20.4): a chip-to-chip CPU copy loses to the blitter |
| CPU takes a wide row when the blitter is busy | Neutral |
| Middle words by blit, CPU edges | Worse (200: 22.2): CPU edge accesses do not overlap the blit |
| BLTPRI off | No effect |
| Background plane 3 by CPU, band-only copy | Worse in 350 |
| Background as a coroutine resumed by the blitter interrupt | Only 650 gained (42.4). It wedged unless the interrupt stayed enabled until the final blit's own interrupt |
| Tiled-colour blits from a chip-RAM palette cache | No gain in the heavy views |
| Repeated-rectangle blits | No gain (heavy view 16.7) |
| AGA FETCH64 (FMODE) | No gain, and the display was reported corrupted |
| Strictly periodic SOFT trigger | Not adopted. The original trigger is kept, and α comes from the actual tick time |
| Triple buffering | Rejected by the user (an extra frame of latency) |
| The slave enabling caches itself | Rejected by the user; left to WHDLoad's options |
| A faster simulation (four times the rate, or the player's car once per PAL field) | Analysed ([simulation-feasibility.md](simulation-feasibility.md)); not pursued, the user's decision |

Other notes:
- CPU span stores are already aligned longwords.
- The large native routines cannot be reshaped for the instruction cache without rewriting game
  code.
- Memory placement offers nothing (see game.md).
- `game:0b5a8` is the idle swap wait, and `game:208e0` is object processing; there is no cheap
  fixed cost.
