# Optional fast planar renderer

Project status: Phases A–D and E1 are complete. Phase E2 stopped at the steady A500 handling gate; Phase E remains incomplete.
See the [current handoff](open-work.md) for completed checks, open gates and resume priorities.

Completion-plan C1 retains a later display handshake for staged scenes: drawing
runs in fast RAM first, then waits immediately before copying to chip RAM. Native
fallbacks and twin reference blocks keep the early wait. The write audit, beam
ordering checks and accelerator gains are in [Current measurements](internals.md#phase-c-measurements-and-decisions).


`CUSTOM1=1` enables the fast-RAM renderer. The option is off by default, including on
68000 systems. It retains the game's planar format, native double buffering and original
simulation/update order. It does not introduce chunky pixels, a new timestep or a frame cap.

On 68020+ with static code installed, fallback scenes also use that raster code,
drawing directly to their native chip bitmap. Only supported cockpit scenes stage
pixels. On 68000/68010 the previous staged-only code routing is retained.

## Implemented path

The slave requests 128 KiB of guest expansion in addition to KickEmu's 256 KiB. Before
loading the game's unflagged hunk it reserves the available guest fast pool, keeping game
code and DMA assets in chip RAM. This reservation is the same with the option off and on.
Staging requires an allocation of at least `$9800` bytes backed by actual fast memory;
WHDLoad expansion backed by slow RAM is rejected. The option then falls back to native
rendering. The increased slave expansion-memory requirement applies even with the option off.

Only the normal main-loop renderer call, returning to game `$ceec`, can stage a scene.
The wrapper checks the supported cockpit clip rectangle, clear extent, inactive chip
back buffer and effect/view flags before redirecting `state+$3ba`. Other calls and
unsupported states execute the native renderer. State offsets use game `$a6e` as their base.

The enabled sequence is:

1. Wait for outstanding native blitter work.
2. Seed rows 150–153 of the four fast planes: 640 bytes total.
3. Keep the native edge table. VERIFY can optionally stage its 816 bytes and redirect
   the pointer at game `$12` for isolated experiments.
4. Invoke the native scene renderer once, with its CPU polygon routine routed to fast code.
5. Complete the display handshake, then transfer rows 19–153 to the native chip back buffer: 21,600 bytes. The block-copy loop
   uses ten registers per `MOVEM`, retaining the 8,000-byte plane stride.
6. Restore the draw pointer, clear-cache pointer and relocated output pointers. The
   scratch experiment also restores the native edge table and pointer.
7. Return to the existing gameplay/HUD work, timer drawing and buffer exchange.

The bitmap remains 32,000 bytes, with 128-byte guards on both sides. The edge table also
has guards in verification builds. The normal clip rectangle is rows 19–149; two native
cockpit seam polygons extend to row 153. Only those four uncleared rows require seeding.
The wrapper requires the original 6,000-byte clear endpoint and 131-row clear length.
The fast path leaves bitplane descriptors and front-buffer pointers in chip RAM.

### Rasterizer and static dispatch

The original planar rasterizer at game `$15b68–$1609b` is copied to fast RAM. Its sixteen
specialized span writers retain their original instructions. Sixteen copies of the native
scanline loop select the matching writers with fixed branch displacements. On 68020 and later each loop uses
three direct LEAs for the remaining plane pointers, removing three MOVEA instructions from
nonempty rows. Its fixed 124-byte slot and return offset are preserved, with three NOPs at
polygon return. The 68000/68010 retain the previous loops. The [raster improvement report](raster-improvements.md) records the small
measured gain and rejected arithmetic changes. A small
per-polygon dispatcher chooses a loop and stores its continuation in data, so drawing
never rewrites the fast code. The shared writer return uses `a6`, which is dead until the
next scanline rebuilds the fourth-plane pointer or the native epilogue restores the state base.

This replaces the original branch-displacement writes at `$16080/$1608a` in the fast path.
Verification checks that the entire copied rasterizer, loops and dispatch table remain
unchanged during captures. Cache selection belongs to the user's WHDLoad `CACHE` and
`DCACHE` options; neither build adds a custom cache policy. The
[accelerator checks](accelerator-cache-testing.md) document native branch rewriting
with static routing disabled, C2’s write-free route and the measurement limits.

The original game hunk and other allocations stay in chip RAM. The normal option moves only the audited bitmap and copied rasterizer.
The optional VERIFY scratch experiment also moves the CPU-only edge table. This keeps their contributions separately measurable.
The native polygon trampoline remains for 68000/68010 fallbacks, diagnostic modes
without static code and verification references.
Return normalization also handles `a4` retaining the colour-table pointer after empty scanlines.
On 68010 and later, the wrapper uses `MOVE CCR` rather than privileged `MOVE SR` when saving
condition codes; installation changes are flushed through WHDLoad's patch service.

## Verification

`CUSTOM4=1` in the VERIFY build twins only the pure background fill and polygon draws.
The native draw and staged draw receive the same input registers. Gameplay, geometry,
clock sampling, random-state changes and effects still execute once. Each completed
staged scene checks:

- Exact scene pixels in all four planes.
- Untouched staging areas, initialized with poison rather than a full-image seed.
- Both bitmap guards and both edge-table guards.
- Exact edge-table contents, including unused entries preserved by seeding.
- Polygon output registers and X/N/Z/V/C flags, translating only known relocated pointers.

The initial conservative full-bitmap prototype passed a clean short run. The narrowed
bitmap path subsequently passed the complete 500-field departure capture: 58 completed
staged scenes, no pixel mismatches and no guard failures. A combined rasterizer/edge-table
short run passed 19 completed staged scenes with no pixel, scratch, register or guard
failures. Its 424 paired polygons also had identical input registers apart from the
intentionally relocated edge-table pointer. The combined block-copy experiment passed the complete ten-second departure route with
66 completed staged scenes and zero failures in every pixel, scratch, register, flag and
guard check. The selected bitmap-and-code path also passed 66 completed scenes in a fresh
full run, with code unchanged and no failures. Its verifier normalizes a separate register
snapshot, preserves already-identical values before interpreting pointer ranges, and returns the raw fast outputs, so comparisons cannot alter the normal path's
intra-renderer behavior. That trace contains 500 VBL callbacks, 67 movement updates,
67 normal scene entries and 66 completed post-render updates; the last scene is incomplete. Verification timing is not gameplay performance.

The original ten-second A500 baseline was repeated from a fresh boot and matched all 500
fields: CPU records, DMA records, initial chip RAM and game imagery. Only the already
excluded three rightmost host-border columns are outside screenshot comparison.
A user-disturbed bring-up run is excluded from performance evidence.

## Measurements

These are emulator measurements, not accelerator-board benchmarks. The short comparisons
use a 68EC020/A1200 setup with 2 MiB chip and 4 MiB fast RAM, caches disabled, the same
Practice route and a window beginning at the first normal driving presentation.
FPS uses complete presentation-to-presentation intervals; incomplete renderer calls are
excluded from scene costs. Faster rendering changes the game's elapsed-time-driven scene
sequence, so end-to-end mean scene costs are not identical-state microbenchmarks.

| Path | Completed presentation intervals / PAL fields | Nominal PAL fps | Mean completed scene cost |
| --- | ---: | ---: | ---: |
| Native, option off | 31 / 96 | 16.146 | 812,168 |
| Fast bitmap only | 31 / 97 | 15.979 | 814,222 |
| Fast bitmap + rasterizer + edge table, plain copy | 45 / 96 | 23.438 | 538,029 |
| Same, register-block copy | 47 / 97 | 24.227 | 517,904 |

Costs are the trace backend's CPU-cycle units. Compare them only within the same CPU/timing
configuration. The combined experimental block-copy path is about 50% faster in presentation rate than the native
short sample; the bitmap-only experiment does not show a worthwhile benefit.
The plain transfer averaged 88,688 cycle units; the block transfer averaged 70,819, a 20%
reduction. The selected block-copy build averaged 4,923 for the 640-byte seed and 15,303
for the remaining wrapper/synchronization/scratch work. Its native scene body, including
fast polygon execution, averaged 426,859.

For an identical-input comparison, the combined twin run measured 424 polygon pairs:
9,892,308 native cycle units versus 3,856,902 fast cycle units, a 61.01% reduction.
These intervals exclude the first pointer-load instruction and verification wrappers on
both sides, and include any interrupt cost occurring during the polygon. They support the
rasterizer result independently of the changed gameplay cadence.

### Independent longer driving comparison

The mode-isolation baseline uses a separate read-only debugger counter over 500 PAL fields
from the first driving presentation, before the [address refinement](raster-improvements.md). All five modes used the same slave and memory layout, changing only CUSTOM
settings. These runs count the native caller at `$bc7c` without instruction profiling.

| Path | Complete intervals / fields | Nominal PAL fps |
| --- | ---: | ---: |
| Option off | 154 / 491 | 15.682 |
| Bitmap only | 154 / 490 | 15.714 |
| Bitmap and code | 218 / 492 | 22.154 |
| Bitmap and scratch | 153 / 489 | 15.644 |
| Bitmap, code and scratch | 218 / 491 | 22.200 |

The bitmap-and-code baseline has an exact fresh-boot repeat of its complete 500-field
presentation sequence. The selected 68020 address refinement measures 218/491 = 22.200 fps
and also has exact repeats. The normal option selects **bitmap plus code**
with the block copy: about **41.3% more
presentations/s** than the native path in this longer window. Scratch relocation adds
only about 0.2% to that result, so it stays an experiment rather than part of the normal
option. The short and longer windows cover different scene sequences and are reported
separately rather than combined into one FPS number.

### 68000 compatibility and tradeoff

On a 68000 with 512 KiB chip and 4 MiB fast RAM, the independent 500-field comparison
measured **106 complete intervals / 468 fields (11.325 fps)** with the option off and
**87 / 465 (9.355 fps)** with it on. That is about **17.4% slower**. The option therefore
remains off by default; enabling it is an explicit choice, not automatic CPU selection.

A 500-field 68000 twin capture with fast bitmap, code and experimental scratch completed
24 staged scenes with no pixel, scratch, register, flag or guard failures. Its fast code
remained unchanged. This tests the 68000 instruction path, including its unprivileged
`MOVE SR`, separately from the 68020 `MOVE CCR` path.

With no fast RAM (512 KiB chip / 1,536 KiB slow), option-off and option-on 100-field captures
both retained every original hook byte and performed zero staged renders. All screenshots
matched, and both had 22 movement updates and 22 presentations on exactly the same fields.
The raw CPU/DMA traces were not bit-identical: their interrupt/instruction phase differed,
and the initial chip snapshots differed in one word outside the game hunk. This fallback
check establishes unchanged hooks, imagery and presentation cadence, not whole-trace identity.

## Reproduction and limits

Build the normal slave with `make -C whdload all`; enable `CUSTOM1=1` in WHDLoad.
`make -C whdload verify` includes the input and comparison fixtures. The additional VERIFY
settings are `CUSTOM2=0` (the normal bitmap-and-code path), `1` (bitmap only), `2` (bitmap, code
and scratch), or `3` (bitmap and scratch); `CUSTOM4=1` enables twins, and `CUSTOM5=2` enters Practice.
`COPY_MOVEM=0` and `FULL_PLANAR=1` are assembly-time experiment overrides, passed through
`make -C whdload verify VASMFLAGS="..."`.

Use `tools/fixed_window.sh` with `ANCHOR=0x14764 FIELDS=500` for movement-onset profiling,
or `ANCHOR=0xbc7c` for driving-only windows. `SWAP_ONLY=1` uses the independent read-only
Practice presentation counter. Captures retain initial/final memory and the exact slave.
The harness rejects a capture that did not reach its requested anchor.

`tools/check_disabled.py CAPTURE` verifies all declared hook bytes against the relocated
original game in an option-off or no-fast capture and audits direct hook-entry branches.
`tools/perf_status.py CAPTURE` checks diagnostics and code immutability.
`tools/perf_report.py CAPTURE` reports completed scene costs, seed/copy costs, presentation
intervals and native elapsed-time deltas. `tools/raster_pairs.py CAPTURE` analyzes paired
polygon costs from a twin capture with fast rasterizer code enabled.

The [loader audit](loader-equivalence.md) resolves Copylock D2 without a runtime patch.
The loaders have explicit allocation/timing differences, so performance comparisons continue
to use the same development loader. The audit covers startup and Practice checkpoints;
the completed [gameplay campaign](gameplay-coverage.md) covers longer routes separately.
The emulator 68030/040/060 matrix is documented separately. Physical-board validation is
outside scope. The bounded gameplay campaign passes 30,623 staged twins and checks native
view/effect fallbacks; it does not certify every combination or justify widening supported
paths. The option remains explicit and off by default.
