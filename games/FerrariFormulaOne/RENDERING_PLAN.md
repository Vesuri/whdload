# High-end rendering performance: profile and work order

Measured 2026-10-15. This is a profiling result and implementation plan, not an
optimization release. Game source and RC2 archive are unchanged.

## Short capture and accuracy

Unmodified RC2, SHA256
`e57c42ec5160f1771146045f81a31c59ff7942f30678e801fb5c00178dd2910d`:
PAL A1200, 68020 at stock 14.18758 MHz, 2 MiB Chip + 4 MiB Fast,
WHDLoad 20.1, CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache. Native automatic
demo, no input or game-state writes. CPU-only game hunks and the performance
payload are in public/Fast memory. DMA buffers remain in Chip.

Warp reaches the 100th `B8Draw` entry. Disable warp, wait eight more draw entries,
then capture 48 complete PAL fields (0.96153 emulated seconds). Eleven complete
`B8Draw` entry-to-RTS spans are used for drawing attribution; partial edge draws
are excluded. Twelve displayed-buffer changes occur in the whole window.
Complete display intervals average 3.9091 fields: **12.7703 FPS** (the short-window
count rate including endpoints is 12.4801 FPS). This is a deliberately short
sample of this scene, not a whole-race average or a new high-end CPU measurement.

A second independent boot runs the same anchor with DMA census only, without
instruction profiling. Both full Chip/Fast snapshots at start and end match
byte-for-byte, as do scheduler contexts, all 48 field cycle totals, DMA counts
by type and first displayed bitplane addresses. Both engine error words are zero.
Thus instruction capture has no observed effect on this window's emulated work
or presentation. No pinned RNG or state normalization is needed for this repeat.

The trace records 13,641,764 of 13,641,792 cycles (99.999795%). The 28-cycle
boundary difference is retained explicitly. Individual field instruction sums
can spill across boundaries; use whole-window accounting and complete call
spans, not per-field instruction sums as wall time. CPU costs include memory/DMA
stalls. They are not pure arithmetic costs or automatically removable time.
Profiler: `e411569ca9e0c30b0cb62b831c88a6dcab4f415517cfcf43fb290d1d5d57171c`.

## Where drawing time goes

Mean **62.634 ms/draw**, range **57.858–71.196 ms**, including interrupts.
The following categories are disjoint and sum to the mean:

| Category | ms/draw | Meaning |
| --- | ---: | --- |
| KickEmu `gfx_WaitBlit` body | 22.163 | Busy polling, CIA delay reads and idle return |
| Native `$2a130–$2a13e` wrapper | 10.558 | Includes library dispatch and Chip instruction-fetch stalls |
| Other drawing work | 28.270 | Includes the 4.923 ms beam-wait stage below |
| Interrupt-level instructions | 1.606 | Recorded IPL > 0 instructions during complete draws |
| Unattributed instruction gaps | 0.036 | Kept separate; not assumed to be interrupts |

There are **4,892 wait-helper calls / 11 draws = 444.7 per draw**: 2,237 enter
the CIA busy path, 2,655 return without that path. There are 67,840 CIA reads.
Inclusive helper spans (including interruptions) total 23.398 ms/draw:
20.178 busy and 3.220 non-busy. These inclusive figures overlap the table above.
A call classified non-busy may already have stalled fetching the Chip-resident
library vector: it does not prove that the blitter was idle at wrapper entry.
The observed graphics base is `$221e`, vector `$213a`; the main wrapper is in
Fast memory. The dispatch JSR ranges from 12 to 16,617 charged cycles.
Do not advertise all 32.721 ms as available savings.

A complementary split by drawing stage is inclusive of its subcalls and IRQs;
do not add it to the previous table:

| Stage / canonical entry | ms/draw |
| --- | ---: |
| Setup | 0.147 |
| Beam synchronization, `B8_65728` | 4.923 |
| Clear selected bitmap, `$6b050` | 4.945 |
| `$6b950` | 3.592 |
| Road preparation/drawing, `$6b368` | 17.084 |
| Optional scene, `$69bb8` | 6.019 |
| Remaining scene/instruments/demo text | 22.574 |
| Final clock/flag/waits/publication | 3.350 |

The direct `$239a0` call at `B8_65d56` alone takes **7.024 ms/draw** and is guarded
by the demo flag. It is a demo-only text cost, not a reason to change player
physics and not representative of every gameplay screen. Presentation clock and
flag calls take 2.014 and 0.946 ms respectively. Preserve visible output.

Largest inclusive wait-helper caller totals (ms/draw) are `$24dc6` 3.906,
`$6b082` 2.878, `$32e6c` 2.612, `$24c28` 2.325, `$6ac42` 2.247 and `$6ac16`
2.157. These overlap road, bitmap operations and sprite drawing above. The
colour routine reaches `$32e34` 315 times: indices 0/2/4/6 occur 44/99/39/133
times. Thus **177/315 (56.2%)** are candidates for the existing exact zero/Q
intermediate-blit elision. This is an operation count, not a predicted FPS gain.

The previous accelerated RC1 tests plateaued at 16.64 FPS (three PAL fields),
with the delay inside drawing. This RC2 020 trace identifies credible causes
of poor scaling; it does not establish 040/060 instruction timings. Blitter,
Chip access and beam waits do not disappear when the processor gets faster.

## Implementation order and decision gates

Each item is one independently switchable, equal-layout A/B change and one
cohesive commit. Re-profile after each accepted change; do not stack assumptions.
Keep CUSTOM2=0 legacy-exact, the 20 ms player/100 ms opponents design, public
CPU allocations and Chip DMA ownership. Do not change the delivered RC2 until
its successor passes the final gates.

1. **Fast-memory WaitBlit dispatch and idle path.** Generalize the audited C4
   `$2a130` shortcut/direct-call machinery for the fine path. Validate native
   signatures and install through its relocation-aware patch ledger. Keep the
   old-Agnus settling reads and final CCR behavior. First retain the existing
   busy helper and CIA pacing; avoid the Chip library vector on the qualified
   path. Audit callers that bypass `$2a130`. Measure wrapper/helper cycles,
   idle/busy counts, actual BLTSIZE ordering and presentation cadence. This is
   first because the measured wrapper/helper pair dominates drawing. Do not
   remove busy waits or claim the dispatch stall disappears rather than moves.

2. **Remove exact zero/Q colour intermediates.** Adapt
   `FerrariFormulaOne_Coarse200Colour.s` to fine-path bindings, without importing
   coarse timing assumptions. Reconfirm `$1c1b8` consumers for this executable;
   preserve clipping, masks, shifts, final cookie-cut, mixed minterms and DMA
   sequencing. Directed tests must cover all four observed minterms, clipped
   edges and overlapping cars. Require fewer colour BLTSIZE operations and
   identical pixels; measure the actual saving at `$32e6c`, not 56% of draw time.

3. **Overlap road preparation with safe buffer handover.** Adapt D2's CPU-only
   `$6a2d0`/`$6b168` preparation before the beam wait, keeping native clear/sky
   order and exact projection results. Use `move.w ccr` on 020+, never the C4
   `move.w sr` save that traps through WHDLoad. Use the fine scheduler's VBL
   counter and its lifetime/reset hooks. Retain line-256 waiting unless a real
   field boundary proves the old displayed buffer reusable. The 4.923 ms wait
   is the observed overlap budget, not guaranteed savings. Verify both buffer
   alternations and intermediate display fields, not just final screenshots.

4. **Reduce repeated text/instrument bitmap work.** Re-profile steps 1–3 first.
   If text remains substantial, investigate `$239a0` and `$24ae0` call chains,
   including the 7.024 ms demo label and clock/flag calls. Cache reusable glyph
   preparation in public memory; retain Chip storage for anything read by DMA.
   Draw suppression requires proof that the destination buffer still contains
   the exact pixels: clearing and double buffering invalidate a simple unchanged-
   value check. Track dirtiness per destination, invalidate on clear/view/menu/
   reload, and test value transitions, both buffers and demo/player modes.

5. **Choose CPU or blitter per measured primitive; then reassess IRQs.** If
   small bitmap operations still dominate, histogram native `$24ae0`, `$32d54`
   and road `$6acxx/$6adxx` operations by size, minterm, shift, clipping and
   overlap. Build exact CPU implementations only for profitable, bounded cases;
   keep the native fallback for the rest and synchronize previous DMA before
   CPU writes. Determine crossover separately for 020, 030, 040 and 060;
   do not derive 040/060 CPU costs from this trace. If IRQ cost remains material,
   port C4's empty-queue BLIT ownership only after rechecking queue use and all
   fine-path release routes. The observed IPL > 0 instruction budget here is only
   1.606 ms/draw, so it is not the first optimization.

For each item, repeat the short matched profile/census, then normal demo,
starting-grid and dense-car **300-presentation** comparisons. Require exact
100-update state/private-fraction comparisons, 30 matched complete RGB frames,
zero engine errors, unchanged elapsed time (60 simulated seconds, absolute error
<=0.25%), and legacy-exact checks. Rendering-only changes must also preserve
intermediate DMA/display ownership. Repeat native throttle, clutch, braking,
restart, steering, manual gears, pause/tow/pit/menu/re-entry, failure cleanup and
restoration of patches/INTENA. Test native player driving as well as the demo:
its 7 ms text cost is workload-specific.

Accept only measured lower draw cost with no same-workload frame-time regression
on 020+Fast and the accelerated configurations. If cost falls but PAL cadence
stays unchanged, record the margin explicitly; do not call it an FPS win. Reject
regressions or unexplained state/frame differences before the next item. Report
mean and p95 frame intervals, both draw and whole-loop costs, and clock error.

The high-end target is to cross from three fields/frame to at most two in the
normal workload (about 25 FPS PAL), while improving grid/dense cases without
regression. This is a target to test on 040/40 MHz + Fast/MMU and 030/060 controls,
not a promised outcome. Emulator qualification cannot establish real-hardware
rates; physical hardware testing remains deferred.

## Evidence and reproduction

Local ignored evidence:
- `tmp/dev/tmp/step5/c4-q03-render-profile-a1200-fast-rc2-trace/`:
  result, address map, snapshots, instruction trace and render/wait/call analyses.
- `tmp/dev/tmp/step5/c4-q03-render-profile-a1200-fast-rc2-census/`:
  matched non-instruction-traced DMA window and presentation analysis.
- `tmp/dev/manifest/render-profile-020-fast.json`: exact inputs, audit and hashes.

From the repository root, source `tmp/dev/amiga/env.sh`. Run
`python3 tmp/dev/tools/capture_render_profile.py a1200-fast` with
`C1_VARIANT=rc2-trace` and
`RELEASE_WHD_ARGS='CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache'`.
After it exits, repeat with `C1_VARIANT=rc2-census RENDER_CAPTURE=census`.
Never overlap these launchers. Run the Python scripts under `tmp/dev/tools/`: `analyze_render_profile.py`
with the trace directory argument, then `analyze_render_waits.py`,
`analyze_render_calls.py` and `audit_render_profile.py`. Scripts and artifacts remain ignored per project
rules. The tracked report preserves the measured results and implementation gates.

The 308 MB raw instruction trace is retained as verified 18.2 MB `detail.bin.gz`;
decompress it to `detail.bin` before rerunning the analysers. Its raw and
compressed SHA256 hashes are in the manifest. No long-running trace is retained.
