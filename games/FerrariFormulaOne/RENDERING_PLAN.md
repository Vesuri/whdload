# High-end rendering performance: profile and work order

Initial profile measured 2026-10-15 against unchanged RC2. Subsequent H2/H3
implementation findings are recorded below. The delivered RC2 archive remains
unchanged; this work is not a new packaged release.

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

1. **H1 — Fast-memory WaitBlit dispatch: discarded (user decision).** The
   direct-call candidate was measured, then completely removed. No experimental
   implementation or build switch remains. See the findings below. Proceed to H2.

2. **H2 — Remove exact zero/Q colour intermediates: accepted.** Adapt
   `FerrariFormulaOne_Coarse200Colour.s` to fine-path bindings, without importing
   coarse timing assumptions. Reconfirm `$1c1b8` consumers for this executable;
   preserve clipping, masks, shifts, final cookie-cut, mixed minterms and DMA
   sequencing. Directed tests must cover all four observed minterms, clipped
   edges and overlapping cars. Require fewer colour BLTSIZE operations and
   identical pixels; measure the actual saving at `$32e6c`, not 56% of draw time.

3. **H3 — Overlap road preparation with safe buffer handover: accepted.** Adapt D2's CPU-only
   `$6a2d0`/`$6b168` preparation before the beam wait, keeping native clear/sky
   order and exact projection results. Use `move.w ccr` on 020+, never the C4
   `move.w sr` save that traps through WHDLoad. Use the fine scheduler's VBL
   counter and its lifetime/reset hooks. Retain line-256 waiting unless a real
   field boundary proves the old displayed buffer reusable. The 4.923 ms wait
   is the observed overlap budget, not guaranteed savings. Verify both buffer
   alternations and intermediate display fields, not just final screenshots.

4. **H4 — Reduce repeated text/instrument bitmap work: accepted.** Re-profile after H2–H3 first.
   If text remains substantial, investigate `$239a0` and `$24ae0` call chains,
   including the 7.024 ms demo label and clock/flag calls. Cache reusable glyph
   preparation in public memory; retain Chip storage for anything read by DMA.
   Draw suppression requires proof that the destination buffer still contains
   the exact pixels: clearing and double buffering invalidate a simple unchanged-
   value check. Track dirtiness per destination, invalidate on clear/view/menu/
   reload, and test value transitions, both buffers and demo/player modes.

5. **H5 — Choose CPU or blitter per measured primitive; then reassess IRQs: accepted.** If
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

## H1 findings and withdrawal (2026-10-15)

The user rejected H1 after measurement: reaching the blitter wait earlier mainly
moves waiting from the Chip library dispatch into the busy helper. All H1 source,
build integration and local experimental builds were removed. The shipped RC2
archive was unchanged and the ordinary source was restored to RC2.

Equal-layout, RNG-controlled, every-update endpoint rendering gives 14 complete
matched draws per arm. Both execute exactly 6,712 WaitBlit calls. Mean total draw
time is **60.102745 -> 60.111022 ms**, effectively unchanged. The wrapper/helper
pair falls from 29.775656 to 29.115451 ms, but busy calls increase from 2,849 to
3,371. CIA reads increase from 86,644 to 91,628. Work outside beam synchronization
falls about 0.876 ms, while the beam wait rises about 0.885 ms. This is not a
material reduction in total draw time.

The completed untraced 020+Fast normal-demo 300-presentation comparison is
13.229790 -> 13.288485 FPS (about 0.44%), mean interval 75.586987 -> 75.253122 ms;
p95 remains 80.127548 ms. Both 60-second elapsed checks take 60.055597 emulated
seconds, with 0.092576% error. These small cadence differences do not establish a
useful high-end improvement. The 040 comparison was stopped at the user's
request; no accelerated result is claimed.

The 100-update oracle passes all 27 state blocks and private physics fractions
exactly. The candidate's independent short trace/census has identical scheduler
contexts, field cycles, DMA counts and displayed bitplane addresses. Complete
RAM snapshots differ at two bytes ($5fa140 and $5fa146) in both endpoints;
therefore full-RAM identity is not claimed. Canonical semantic blocks match.
The remaining frame, grid/dense, controls and lifecycle qualification was not
completed: this is a rejected experiment, not an accepted optimization.

Local results and verified compressed traces remain as evidence under
`tmp/dev/tmp/step5/c4-q03-*-h1-*` and are indexed by
`tmp/dev/manifest/render-h1-withdrawal.json`. Experimental code and slaves are
not retained. H2 was the next implementation step.

## H2 zero/Q colour intermediates (2026-10-15)

`RenderColour.s` ports the accepted C4 colour operation to the fine path. The
entire native table/routine is signature checked before the existing patch
ledger installs the hook. Zero disables B DMA; Q uses the original Q source
instead of first copying it to scratch. Mixed minterms, clipping, shifts, masks,
final cookie-cut BLTSIZE and the wait before each plane remain native. There is
no H1 dispatch change, new DMA allocation or interrupt ownership change.

The fresh SPS 0481 relocation/alias audit confirms five references to `$1c1b8`:
allocation guard, assignment, free argument, colour destination and cookie-cut
source. Only the cookie-cut consumes scratch contents. The independent model
passes all 32 Boolean and 5,760 shifted/clipped/row cases.

Fourteen exact endpoint draws have identical plane/minterm and clipping/shift
sequences. Intermediate colour blits fall **420 -> 182** (56.67%); all **420**
final cookie-cut blits remain. Inclusive WaitBlit time at `$32e6c` falls
**1.171216 -> 0.428373 ms/draw**, with calls **420 -> 182** and busy calls
**19 -> 2**. Total matched draw time is **60.114767 -> 60.111228 ms**; work
outside beam synchronization falls **56.082881 -> 54.847298 ms** (1.236 ms,
2.20%). The beam wait absorbs that margin in this endpoint fixture, so this is
not a matched-draw FPS gain. Ordinary and dense workloads are measured separately.

The normal 020+Fast 60-second run takes **60.055597 seconds** in both arms,
**0.092576%** error. The 100-update comparison matches all 27 semantic blocks
and private physics fractions exactly. Normal, grid and dense fixtures each
match 30 complete 754 x 576 RGB frames: 90 exact comparisons, with no crop or
pixel tolerance. The frame observer initializes exporter padding, as established
for C4; performance measurements use the timing observer.

All four short traces keep blitter/bitplane DMA in Chip memory. Candidate trace
and independent census match scheduler contexts, field cycles, DMA counts and
first displayed bitplane addresses. Coverage is 99.999795% (28 boundary cycles).
Whole RAM snapshots differ at two bytes, `$5fa140` and `$5fa146`, at both ends;
full-RAM identity is not claimed. The separate semantic/private-state gate is exact.

The user accepted H2 on these completed results and stopped the remaining
qualification on 2026-10-15. The following are equal-layout, warp-off comparisons
of 300 complete presentation intervals. Census-window boundaries are excluded;
the 020 dense run required two windows. Fixed grid/dense fixtures retain all
seven opponents. No completed comparison regresses in mean or p95.

| Emulator / scene | FPS control → H2 | Mean ms control → H2 | p95 ms control → H2 |
|---|---:|---:|---:|
| a1200-fast / normal | 13.230 → 13.300 | 75.587 → 75.186 | 80.128 → 80.128 |
| a1200-fast / grid | 12.480 → 12.480 | 80.128 → 80.128 | 80.128 → 80.128 |
| a1200-fast / dense | 5.703 → 6.240 | 175.346 → 160.255 | 180.287 → 160.255 |
| 030-50 / normal | 16.243 → 16.640 | 61.565 → 60.096 | 80.128 → 60.096 |
| 030-50 / grid | 14.386 → 16.640 | 69.511 → 60.096 | 80.128 → 60.096 |
| 030-50 / dense | 9.984 → 9.984 | 100.159 → 100.159 | 100.159 → 100.159 |
| 040-40 / normal | 16.622 → 16.640 | 60.162 → 60.096 | 60.096 → 60.096 |
| 040-40 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 040-40 / dense | 9.984 → 9.984 | 100.159 → 100.159 | 100.159 → 100.159 |
| 060-50 / normal | 16.603 → 16.640 | 60.229 → 60.096 | 60.096 → 60.096 |

These are emulator observations with the calibrated timing observer, not physical
CPU rankings. Accelerated tests use explicit real-frequency, cycle-exact settings
(030/50, 040/40 and 060/50; 8 MiB Fast). 040/060 timing profiles have MMU off;
no new 040/MMU/32 MiB control result is claimed. The normal high-end workload
still takes three PAL fields; H2 does not meet the 25 FPS target.

Remaining H2 checks were deliberately stopped: 060 grid candidate/dense,
native input/manual gears, 040/MMU/32 MiB driving, pause/tow/pit/menu/re-entry,
patch/INTENA restoration, signature-failure injection and fresh CUSTOM2=0 /
CUSTOM1 comparisons. Prior RC2 qualification is historical evidence, not a
substitute for those H2 reruns. H2 is accepted for continued development, not
fully release-qualified. Human full races and physical hardware remain deferred.

The independently reproduced slave is 261,512 bytes, SHA256
`0a26fe52fd0e27e476dacdc53401c30b923a5d7dd7099bb025d8a06ee1d798b2`.
The equal-layout control differs only in the immutable H2 preset. The 68000 and
chip-only 020 payloads are unchanged. CUSTOM2 remains default-off. The delivered
RC2 LHA is unchanged. H3 was next; its findings follow.

Local evidence: `tmp/dev/manifest/render-h2-validation.json`,
`render-h2-performance.json`, `render-h2-matched-profile.json`,
`render-h2-scratch.json`, `render-h2-dma.json` and `render-h2-traces.json`.
The four raw traces were compressed and their decompressed hashes verified;
analysers require decompression. Harness scripts and diagnostic builds stay ignored.

## H3 accepted: road preparation and safe handover (2026-10-15)

`RenderRoad.s` moves the native CPU-only road transformation/clipping before
beam synchronization on the 020+Fast path. It preserves the projection's
D0-D7/A0-A6 and CCR result, restores it at the original road call boundary,
and retains the native clear/sky ordering. The fine scheduler's field counter
permits buffer reuse only after a field boundary; otherwise line-256 waiting
remains. The public lifetime reset clears the workspace. CCR reads avoid the
WHDLoad traps caused by SR reads. No native hook, allocation, or interrupt
ownership change is introduced by H3; the coarse payloads remain byte-identical.

The first candidate passed completed-frame checks but failed intermediate-field
comparison: native flag drawing temporarily overwrote the clock on the displayed
bitmap before clock drawing repaired it. Earlier completion exposed that state.
The corrected candidate composes both native flag/clock passes on the back buffer
by temporarily aliasing the second pointer view to the first, then restores it.
All native drawing operations and the final blitter-completion wait remain.
This correction is part of safe H3 handover, not a pixel-comparison exclusion.

Fourteen matched endpoint draws fall from **60.110256 to 59.484553 ms**, a
**0.625703 ms / 1.04%** saving. Mean draw-entry interval falls from 64.366560 to
63.705035 ms in this every-update endpoint fixture; this is not ordinary-demo
FPS. Beam waiting falls from 5.640759 to 1.807914 ms, but most of that is replaced
by preparation or shifts in other waits. The net saving is the figure above.

All observed projection data/address registers, plane/minterm sequences,
clipping and clear destinations match. The trace's raw SR copy is not a CCR
oracle: the observer copies lazy `regs.sr` without MakeSR, while the candidate's
CCR save materializes the flags. The native resume instruction immediately
replaces NZVC. No architectural-CCR equality claim is made from that raw field.

All 15 preparation-to-clear transitions are safe: eight cross a hardware field;
seven retain the line-256 wait. Both buffer alternations are covered. After
collapsing repeated identical interior fields, all 15 distinct bitplane DMA data sequences
match exactly between arms, with no pixels excluded. The rejected first version
had 22 sequences, including transient flag/clock corruption. Finished-frame
checks independently match 30 complete RGB images in each normal/grid/dense
scene (90 comparisons; all 180 retained images rehashed).

Intermediate JPEGs are not all identical: the pre-existing B8 `COLOR00=1`
diagnostic write (introduced in 38b2c61, absent from the original game) moves
with draw timing. All 15 stable decoded RGB images match; 14 transition images
per arm have different palette-pulse boundaries. The CPU colour-write values
and all copper palette writes, including beam slots, are unchanged. This is
documented separately from the corrected flag/clock corruption; no image mask
is used. Removing the inherited palette pulse remains separate cleanup work.

The 100-update state/private-fraction gate is exact. The 60-second clock test
takes 59.975470 seconds in the control and 60.015534 in H3, absolute errors
0.040900% and 0.025883%, both below 0.25%.

| Emulator / scene | FPS control → H3 | Mean ms control → H3 | p95 ms control → H3 |
|---|---:|---:|---:|
| a1200-fast / normal | 13.312 → 13.312 | 75.120 → 75.120 | 80.128 → 80.128 |
| a1200-fast / grid | 12.480 → 12.844 | 80.128 → 77.857 | 80.128 → 80.128 |
| a1200-fast / dense | 6.240 → 6.316 | 160.255 → 158.319 | 160.255 → 160.255 |
| 030-50 / normal | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 030-50 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 030-50 / dense | 9.984 → 9.984 | 100.159 → 100.159 | 100.159 → 100.159 |
| 040-40 / normal | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 040-40 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 040-40 / dense | 9.984 → 10.004 | 100.159 → 99.959 | 100.159 → 100.159 |
| 060-50 / normal | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 060-50 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 060-50 / dense | 9.984 → 10.004 | 100.159 → 99.959 | 100.159 → 100.159 |

These are 300 complete warp-off presentation intervals with the calibrated
emulator used for H2, not physical CPU rankings. Accelerated timing profiles
use 8 MiB Fast and explicit real-frequency cycle settings; 040/060 timing runs
have the MMU off. The functional 040/MMU/32 MiB control check is separate.
Normal high-end presentation remains at three PAL fields; the two-field/~25 FPS
target is still open.

Native throttle/clutch, coast, braking, restart and steering pass on 020+Fast
and 040/MMU/32 MiB. F1 manual up/down shifts, launch, braking to zero and restart
pass. Native pause preserves exact pending time; tow restores all 905 owned
patch words. INTENA is unchanged throughout the observed lifecycle. Pit/menu/
session changes and re-entry start a fresh epoch with a zeroed H3 workspace;
21 subsequent updates and fresh colour-hook bindings pass. The first manual
replay omitted track entry and failed before testing controls; restoring the
recorded native entry sequence fixed the harness without changing game code.

The independent ordinary trace/census boots have identical complete start/end
Chip/Fast snapshots, scheduler contexts, DMA counts and displayed bitplane
addresses. All DMA remains Chip. Recorded cycle coverage is 99.999993%, with
one boundary cycle unrecorded. Both CUSTOM1 settings pass the unchanged
controlled CUSTOM2=0 exact-state gate on A500, A500+Fast, chip-only 020 and
020+Fast. Deliberate colour-signature corruption reaches the WHDLoad error
route before installing that hook.

The ordinary post-H3 trace has 11 complete draws averaging 62.873917 ms in its
own scene: the remaining scene/HUD stage costs 22.118482 ms, including the
7.215498 ms demo-label call. This is fresh H4 input, not an A/B speedup claim.

Local evidence: `tmp/dev/manifest/render-h3-validation.json`,
`render-h3-performance.json`, `render-h3-matched-profile.json`,
`render-h3-palette.json`, `render-h3-palette-dma.json`,
`render-h3-field-rgb.json`, `render-h3-build-audit.json`,
`render-h3-dma.json` and `render-h3-traces.json`. Raw traces were compressed
and decompressed hashes verified. The rejected first candidate is indexed by
`render-h3-v1-rejection.json`; harnesses, fixtures and game data remain ignored.

The independently reproduced 262,056-byte slave has SHA256
`ac034f9786055bcb04c45383740def6cf249bf0910260dbc322c98461f15a8c2`.
CUSTOM2 remains default-off. The RC2 preinstalled archive is unchanged.
Human full races and physical hardware remain deferred.

**Next at the H3 checkpoint: H4 (now completed below).** Separate pre-release cleanup **B8-PAL** is removal
of the inherited unconditional diagnostic `COLOR00` pulse described above;
H3 preserves its values and does not claim identical transition-field JPEGs.

## H4 accepted: batch demo text and remove duplicate clock writes (2026-10-15)

`RenderText.s` replaces the driving demo's 21 separate glyph operations with
one packed bitmap operation per destination. It predecodes the fixed label's
font columns but rebuilds its pixels from the live font on every draw. The
192-byte CPU workspace is public memory. After WaitBlit, it copies the packed
rows into the existing 1,020-byte Chip colour scratch; native `$24ae0` retains
shifts, masks, foreground/background minterms and first/second buffer order.
A final WaitBlit returns scratch to native ownership. H2's whole-overlay audit
establishes that the completed sprite cookie-cut is its only native data reader.
There is no new allocation, native patch site or interrupt ownership.
Changed label, position, style, view or unsupported font dimensions retain the
native text path.

The clock optimization applies during player driving as well as the demo.
H3 temporarily gives both native HUD pointer views the same back buffer.
`FF1RenderClockDigit` draws each digit once when those pointers are identical;
the native immediate second overwrite has the same source, coordinates and
colours, with no intervening writer. Its masked foreground/background operation
is idempotent. Different destinations and other native display modes retain
`$23288`. This never suppresses a later frame's draw: every clear, buffer swap,
font/value change and re-entry gets fresh pixels. No destination cache needs
to survive a view/menu/reload. The public reset table also clears the workspace.
Flag rendering is unchanged; it remains separate work for the next profile.

Fourteen complete matched endpoint draws cost **60.156836 → 55.786248 ms**,
a **4.370588 ms / 7.27%** reduction. The matched entry interval costs
**64.377998 → 60.080593 ms**. The demo label falls **7.245341 → 1.549847 ms**,
with **126 → 6** BLTSIZE operations. The clock falls **2.091870 → 1.153091 ms**,
with **42 → 21** operations. Beam waiting absorbs some primitive savings;
the reductions must not be summed and presented as additional whole-frame gain.
These endpoint fixtures are not ordinary-demo FPS measurements.

The equal-layout control disables both H4 operations with one immutable preset
byte. All 100 updates match all 27 semantic blocks and private fractions exactly.
Normal, grid and dense each pass 30 complete 754 x 576 RGB comparisons, without
cropping, masks or pixel tolerance. All 180 acceptance PNGs are independently
rehashed. The first normal image run exposed an observer scheduling issue:
its two-field capture allowed the faster arm to skip updates 2, 11 and 27;
all common update images were exact. The corrected normal/dense sampling fixes
30 update numbers (1, 5, 10, …, 145), with no writes to game state and no change
to image equality. Grid's original 30 consecutive samples already passed.

The 48-field paired trace has 15 exact shared interior bitplane-DMA sequences;
the faster arm reaches one additional frame. Repeated identical fields are collapsed; shared sequences align at zero,
with every transition retained. Native projection registers, clipping, colour
planes and clear destinations match. Both buffer banks and all observed safe
handover checks pass. All DMA stays Chip. The inherited **B8-PAL** diagnostic
pulse still changes scanline with timing, so identical full transitional RGB
fields are not claimed. H4 makes no palette change; cleanup remains separate.

The independent pixel model passes 400 random live-font/stride cases, and all
32 Boolean cases for clock overwrite idempotence. The complete emulator image
checks provide the native shift/mask check. Both 60-second clock errors remain
below 0.25%; the exact values are recorded below. Native F3 throttle/clutch,
coast/brake/restart/steering, F1 manual gears, and the 040/MMU/32 MiB control
configuration pass. Pause retains exact pending time; tow restores the owned
patch ledger, INTENA remains unchanged, and pit/menu/session re-entry clears
the H3/H4 workspaces before the fresh epoch. Both CUSTOM1 settings pass the
controlled CUSTOM2=0 exact-state gate on all four base profiles. The inherited
signature-failure path rejects a deliberately damaged signature before its hook
is installed. The 000 and chip-only 020 payloads remain byte-identical to H3.

The following are 300 complete warp-off intervals, with census-window boundaries
excluded. All twelve comparisons pass mean and p95 no-regression. These are
fresh H4 equal-layout baselines; do not combine their raw FPS with historical
H3 measurements from a different binary layout. All seven opponents remain in
the grid/dense fixtures and their incomplete-projection counter stays zero.

| Emulator / scene | FPS control → H4 | Mean ms control → H4 | p95 ms control → H4 |
|---|---:|---:|---:|
| a1200-fast / normal | 13.312 → 15.266 | 75.120 → 65.504 | 80.128 → 80.128 |
| a1200-fast / grid | 12.978 → 14.582 | 77.056 → 68.576 | 80.128 → 80.128 |
| a1200-fast / dense | 8.315 → 8.883 | 120.258 → 112.579 | 120.191 → 120.191 |
| 030-50 / normal | 16.640 → 17.057 | 60.096 → 58.627 | 60.096 → 60.096 |
| 030-50 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 030-50 / dense | 9.984 → 12.480 | 100.159 → 80.128 | 100.159 → 80.128 |
| 040-40 / normal | 16.640 → 17.914 | 60.096 → 55.822 | 60.096 → 60.096 |
| 040-40 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 040-40 / dense | 10.004 → 12.480 | 99.959 → 80.128 | 100.159 → 80.128 |
| 060-50 / normal | 16.640 → 17.619 | 60.096 → 56.757 | 60.096 → 60.096 |
| 060-50 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 060-50 / dense | 10.004 → 12.480 | 99.959 → 80.128 | 100.159 → 80.128 |

60 simulated seconds, control: **59.995501699 s**, absolute error **0.007498%**.
60 simulated seconds, candidate: **60.015533586 s**, absolute error **0.025883%**.

The accelerated timing profiles use the calibrated observer and explicit
real-frequency cycle settings: 030/50, 040/40 and 060/50, 8 MiB Fast. The
040/060 timing runs have MMU off; the functional 040/MMU/32 MiB check is separate.
These emulator measurements do not establish physical CPU rankings or a
complete human-driven race. The normal high-end target remains two PAL fields
(~25 FPS); the table records the actual outcome, not an assumed target pass.

The independent ordinary trace/census boots have identical complete start/end
Chip/Fast snapshots, scheduler contexts, every field cycle count, DMA counts
and displayed bitplane addresses. Coverage is 99.999993%, with one boundary
cycle unrecorded out of 13,641,792. All DMA addresses stay below $200000.

The fresh post-H4 ordinary trace has 12 complete draws averaging **59.186521 ms**
in its own scene; this is H5 input, not a paired saving against the older
ordinary captures. Remaining scene/HUD costs **17.330322 ms**, road
**13.460200 ms**, optional scene **7.901218 ms**, clear **5.289644 ms** and
beam wait **3.246725 ms**. The label is **1.868465 ms**, clock **1.177270 ms**.
There are **303.58 WaitBlit calls/draw** (1,340 busy / 2,303 idle over those
12 draws), 78,396 CIA reads and **24.010989 ms/draw** inclusive waits. These wait
costs overlap the stage totals. Large caller totals are clear `$6b082` 3.037 ms,
bitmap `$24c28` 2.592 ms, road `$6ac16` 2.536 ms / `$6ac42` 2.303 ms and
bitmap `$24dc6` 2.300 ms. H5 should histogram actual primitive work and choose
bounded CPU alternatives; H1's discarded dispatch-only change stays removed.

The independently reproduced slave is 263,532 bytes, SHA256
`f4f09229e73699fe278df126cc9d3ab614df449b2a4d2e26384d16ca1911fa0f`.
CUSTOM2 remains default-off. The delivered RC2 LHA is unchanged. Human full
races and real hardware remain deferred. **H5 is next**, using the fresh post-H4
profile for primitive selection; **B8-PAL** remains separate pre-package cleanup.

Local evidence: `tmp/dev/manifest/render-h4-validation.json`,
`render-h4-performance.json`, `render-h4-matched-profile.json`,
`render-h4-source-audit.json`, `render-h4-build-audit.json`,
`render-h4-text-model.json`, `render-h4-dma.json` and `render-h4-traces.json`.
Raw traces are compressed with verified decompressed hashes; harnesses and
fixture builds remain ignored. The earlier demo-only iteration and observer
sampling diagnostic remain separately labelled, not reused as final acceptance.

## H5 accepted: bounded CPU font glyphs (2026-10-15)

`RenderBitmap.s` replaces the native bitmap operation only for byte-aligned
8 x 8 glyphs from either live native font, with three destination planes and
48-byte destination rows in the driving pointer views. It reads each font row
once, then writes eight bytes per plane with the exact foreground/background
operation. Each selected glyph replaces three blits with 24 CPU byte writes.
Other sizes, shifts, source types, multi-plane sources and unsupported coordinates
retain the native routine. Road lines/fills and sprite colour operations remain
on the blitter. The post-H4 histogram, not processor speed alone, selected this
small class; it does not establish a general CPU/blitter crossover curve.

The already-owned driving path is separately covered by 268 full-plane/CCR
comparisons on 020, plus the actual rendering profiles.

The previous DMA is completed by native WaitBlit before reading the font or
writing destination pixels. Conditional native OwnBlitter/DisownBlitter remains.
The same KickEmu ownership implementation explicitly preserves its scratch
registers. No font/destination cache or new DMA allocation is introduced; the
CPU code is in the existing public/Fast payload. The existing hunk ledger owns
the six-byte entry patch and restores it on release. Both A500 and chip-only 020
payloads remain byte-identical to H4. The final path also clears X before the
native exit, matching the original final-plane subtraction; it never reads SR.

The equal-layout control validates the same entry signature but leaves that
entry untouched. All new hook/selection overhead is charged to the candidate.
The preset is the sole differing binary byte. An earlier dispatch-bearing
control was retained as a diagnostic, not reused as final acceptance.

Each CPU profile passes 268 directed native-versus-CPU comparisons of all 30,960
destination bytes and the complete CCR: all 64 foreground/background pairs,
both fonts and byte positions, screen edges, and 12 shifted/size fallback cases.
The independent bit-level model passes 3,072 whole-row cases. The benchmark
executes 20,000 glyph calls per arm, acquiring/releasing native ownership per
call, after two settled VBLs with warp off;
readback verifies the control's original entry and the candidate's hook.
VBL endpoint resolution is approximately 1.002 μs/glyph. These are calibrated
emulator results, not physical CPU rankings or predictions for larger bitmaps.
The actual matched driving trace selects seven clock glyphs per draw; their
CPU function mean is approximately 82 μs with ownership already held.

| Emulator | Native μs/glyph | CPU μs/glyph | Reduction |
|---|---:|---:|---:|
| a1200-fast | 159.254 | 121.193 | 23.9% |
| 030-50 | 200.319 | 47.075 | 76.5% |
| 040-40 | 173.276 | 39.062 | 77.5% |
| 060-50 | 173.276 | 39.062 | 77.5% |

The 15 complete matched draws average **55.884396 → 55.790830 ms**, a
**0.093565 ms / 0.17%** reduction. Whole-loop matched entry intervals are
**60.081409 → 60.081141 ms**.
The 16 shared interior bitplane-DMA sequences match from the first sequence
after collapsing repeated identical fields. Native projection registers, clipping,
colour planes, clear destinations and safe buffer handovers remain exact.
Beam waiting absorbs some primitive savings; the draw result is not an assumed
whole-frame speedup.

All 100 simulation updates and private fractions match exactly. Normal, grid and
dense each pass 30 complete RGB images without pixel masks or tolerance. Both
60-second elapsed tests pass the 0.25% gate. All twelve 300-interval performance
pairs below pass mean and p95 no-regression; retain their fresh equal-layout
baselines rather than summing speedups across older binary layouts. Accelerated
profiles use the calibrated real-frequency emulator settings; the functional
040/MMU/32 MiB check is separate from MMU-off timing.

| Emulator / scene | FPS control → H5 | Mean ms control → H5 | p95 ms control → H5 |
|---|---:|---:|---:|
| a1200-fast / normal | 15.297 → 15.392 | 65.371 → 64.970 | 80.128 → 80.128 |
| a1200-fast / grid | 14.304 → 14.597 | 69.911 → 68.509 | 80.128 → 80.128 |
| a1200-fast / dense | 7.131 → 7.145 | 140.223 → 139.956 | 140.223 → 140.223 |
| 030-50 / normal | 17.077 → 17.354 | 58.560 → 57.625 | 60.096 → 60.096 |
| 030-50 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 030-50 / dense | 12.480 → 12.480 | 80.128 → 80.128 | 80.128 → 80.128 |
| 040-40 / normal | 18.000 → 18.264 | 55.555 → 54.754 | 60.096 → 60.096 |
| 040-40 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 040-40 / dense | 12.480 → 12.480 | 80.128 → 80.128 | 80.128 → 80.128 |
| 060-50 / normal | 17.619 → 18.022 | 56.757 → 55.488 | 60.096 → 60.096 |
| 060-50 / grid | 16.640 → 16.640 | 60.096 → 60.096 | 60.096 → 60.096 |
| 060-50 / dense | 12.480 → 12.480 | 80.128 → 80.128 | 80.128 → 80.128 |

Native F3 throttle/clutch/coast/braking/restart/steering, F1 manual gears,
040/MMU/32 MiB controls, pause/tow/pit/menu/re-entry and patch restoration pass.
The new entry is verified after reload. The CPU-write audit matches every
selected write to an actual byte bus write.
Matched-scene destinations are not fetched in the same field. Three ordinary
trace fields also update a visible HUD glyph, but all affected rows and planes
have already been fetched before any update (minimum margin 21,709 Chip slots).
No selected write overlaps the affected display fetch interval. Both CUSTOM1
settings retain the controlled four-profile CUSTOM2=0 exact-state gate. A deliberately damaged
bitmap signature exits before installing its hook. The independent ordinary
trace/census audit retains exact full snapshots, contexts and DMA; all DMA
addresses stay in Chip memory.

The historical H4 dense run recorded 8.883 FPS; the fresh H5 control already
records 7.131 FPS before the H5 hook is installed. Their performance windows
start after 557 versus 695 simulation updates even though both warm up 100 draws.
All 30 shared normal/dense completed images and seven shared grid images match
at fixed updates across H4-candidate/H5-control. The live-physics performance
fixtures and binary layouts are not identical historical timing experiments;
the cause of that absolute-rate shift remains unassigned. Acceptance uses the
fresh native-entry control pair; historical raw FPS values are reported separately.
See `tmp/dev/manifest/render-h5-historical-baseline.json`.

The fresh ordinary trace has 288.58 WaitBlit calls/draw,
24.301731 ms/draw inclusive waits, and
1.530963 ms/draw of interrupt-level instructions.
The remaining IRQ budget is not empty-queue BLIT service: INTENA bit $40 is
already clear at every captured field start and throughout all recorded CPU/
copper INTENA writes, including conflict records. The fine path therefore
already satisfies C4's interrupt-disable condition; no ownership port is needed.
IRQ ownership remains unchanged. The histogram leaves larger bitmap, road and
sprite work native; further optimization needs a new measured case rather than broader
unvalidated CPU thresholds. H1's discarded dispatch-only experiment stays absent.

The existing **B8-PAL** diagnostic COLOR00 pulse remains separate cleanup.
Exact bitplane sequences and completed RGB images do not claim identical full
transitional RGB fields while that timing-dependent pulse exists. No palette
masks or edits were used. The normal ~25 FPS target is not reached.

The independently reproduced slave is 264,520 bytes, SHA256
`57900954b6eb18f1691f3ff8f9b51bcb4beb8a6c3456b6d33f1268cc810c9316`.
CUSTOM2 stays default-off. RC2 LHA is unchanged;
no successor packaging or broad release qualification is claimed. Human full
races and real hardware remain deferred. H1–H5's implementation work is closed
(H1 discarded); B8-PAL cleanup and successor packaging remain separate work.

Local evidence: `tmp/dev/manifest/render-h5-validation.json`, `render-h5-histogram.json`,
`render-h5-oracles.json`, `render-h5-matched-profile.json`,
`render-h5-performance.json`, source/build/model/DMA audits and compressed traces.
