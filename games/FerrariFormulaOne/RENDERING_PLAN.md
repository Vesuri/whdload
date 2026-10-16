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
In this 020+Fast trace, the remaining IRQ budget is not empty-queue BLIT service: INTENA bit $40 is
already clear at every captured field start and throughout all recorded CPU/
copper INTENA writes, including conflict records. This observation does not
extend to 030/040/060: their startup graphics timer enables BLIT, as established
by the H6/H7 investigation below. H5 left IRQ ownership unchanged.
The histogram leaves larger bitmap, road and
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

## High-end 25 FPS profile and plan H6–H16 (2026-10-15)

Short diagnostic profile of HEAD `25ca4b9` (264,520-byte slave). Only test
fixtures were built; game code is unchanged. Full analysis:
`tmp/dev/docs/HI25_PLAN.md`; evidence index: `tmp/dev/manifest/hi25-profile.json`.

### Frame budget

`B8Draw` publishes the previous frame, prepares the road, waits for line 256
(or a passed field), then clears and draws. A frame is shown every two fields
(40.06 ms, 24.96 FPS) only if post-wait drawing + ticks (~1.6–1.8 ms on 040)
+ publish/road preparation (1.3 ms) fit in 40.06 ms. Post-wait drawing must
therefore stay below about 37 ms; target 33 ms for margin.

### Profile: 040/40, 30 traced fields after 100 warm-up draws

`solo` is the dense-pack pose with all seven opponent draw calls counted and
returned before any sprite work. `default` is the accelerated profile used for
H2–H5; `cycle-exact` adds `--uae_blitter_cycle_exact=true`. Values are ms per
drawn frame; FPS values are 300 complete presentations.

| Scene | Blitter | Post-wait draw | WaitBlit spin | BLIT IRQ | CPU | FPS |
|---|---|---:|---:|---:|---:|---:|
| solo | default | 37.6 | 24.0 | 9.8 | 5.1 | 23.11 |
| normal | default | 41.2 | 26.0 | 11.1 | 5.5 | 18.26 (H5) |
| grid | default | 44.3 | 28.4 | 11.6 | 5.7 | 16.64 |
| dense | default | 71.7 | 55.5 | 11.8 | 5.8 | 12.48 (H5) |
| solo | cycle-exact | 42.8 | 26.4 | 9.9 | 7.8 | 16.64 |
| grid | cycle-exact | 50.0 | 31.0 | 11.6 | 8.7 | 16.64 |
| dense | cycle-exact | 85.2 | 60.2 | 12.2 | 14.1 | ~10 (trace) |

The 040 CPU is not the limit: drawing is mostly the CPU waiting for the blitter,
and simulation ticks cost about 0.8 ms each.

**Correction to the H5 IRQ audit.** BLIT was disabled (INTENA `$67AC`) only in
that 020+Fast trace. On 040, INTENA is `$67EC`. The level-3 handler runs about
100–120 times per field, 99% of them for BLIT, about 37 µs each including
WHDLoad's VBR glue, with the blitter idle. No `$8040` write occurs inside the
windows, so the bit is set earlier. A diagnostic fixture that writes INTENA
`$0040` before each draw (no ownership or restore handling) measures:

| CPU | Scene | Blitter | Current FPS | BLIT IRQ off |
|---|---|---|---:|---:|
| 040/40 | solo | default | 23.11 | 24.96 (all 2 fields) |
| 040/40 | grid | default | 16.64 | 24.96 (all 2 fields) |
| 030/50 | grid | default | 16.64 | 24.96 (all 2 fields) |
| 060/50 | grid | default | 16.64 | 24.96 (all 2 fields) |
| 040/40 | solo | cycle-exact | 16.64 | 24.96 (all 2 fields) |
| 040/40 | grid | cycle-exact | 16.64 | 19.97 (150 × 2, 150 × 3) |

**Blitter model.** `uae_cpu_cycle_exact=true` does not enable
`blitter_cycle_exact`, so H2–H5 accelerated FPS used an approximate blitter.
Cycle-exact blitting adds 5–6 ms per frame. Real hardware is expected to be
closer to the cycle-exact model; physical testing remains deferred.

**Blit census** (grid, cycle-exact, BLIT IRQ off). The blitter is busy 14.0 of
20.0 ms per field and 31% of slots stay free. Per field:

| Blit type | Count | ms | Use |
|---|---:|---:|---|
| ABCD cookie-cut | 13.3 | 3.78 | cars, cockpit |
| D-only fill | 3.6 | 2.73 | `$6b050` background, `$6b950` |
| BCD | 36.9 | 2.63 | mostly 1-row road spans |
| CD exclusive fill | 0.8 | 2.04 | full-width 24 × ~103 road fills, 2.5–2.9 ms each |
| line | 49.2 | 1.43 | road edges |
| ABD | 9.9 | 1.38 | masks |

Gaps between consecutive blits are 9–22 µs and total 1.9 ms per field.

### Work order

One switchable equal-layout change per commit, re-profiled after each
acceptance. Keep the H-series rules and gates: CUSTOM2=0 legacy-exact, the
68000/chip-only payloads byte-identical, Chip DMA ownership and the 20 ms
player / 100 ms opponent design. Add solo frames and cycle-exact profiles to
the gates.

1. **H6 — Measurement baseline: complete.** Add `030-50-bce`, `040-40-bce` and
   `060-50-bce` profiles and a 68EC030 trace profile (the full-MMU 68030 loop
   is not instrumented). Adopt the solo fixture, the 040/060 measurement
   emulator and the `analyze_hi25_*` tools. Record 300-presentation baselines.
   "25 FPS" means all 300 complete intervals are two fields.
2. **H7 — Fine-path BLIT interrupt ownership: accepted in the reduced scope below.** Port C4
   `FF1C4BlitAcquire/Restore`. First identify the enabler and prove the gfx
   blit queues stay empty while racing. Acquire at epoch start, on resume and
   at each `B8Draw`; restore on pause/tow/pit/menu/exit/fault/unload.
3. **H8 — Re-profile** on cycle-exact profiles and rank H9–H13 by the residual.
4. **H9 — Exact road-fill narrowing** to the edge-word span of each band
   (fill carry resets per row; the planes are zero outside the edges).
   Expected −1.5 to −3 ms.
5. **H10 — CPU background fills on 030+** for `$6b050`'s D-only fills, gated
   by per-CPU micro-benchmarks. Expected −2 to −3 ms.
6. **H11 — Overlap the top-region flag/clock/demo text with long blits,**
   after proving those rows have no later writer. Expected −1.5 to −2.3 ms.
7. **H12 — Inter-blit latency: dropped by user decision (2026-10-15).**
   No implementation remains or is planned.
8. **H13 — Cockpit, gauges and mirrors** (`$6ba18`, `$6c0d0`, `$6adf8`,
   `$6bbfc`, `$6ae70`, `$6af7e`; ~10 ms per frame): opaque runs as A→D copies,
   bounded CPU gauge segments. Expected −2 to −4 ms.
9. **H14 — Optional:** bit-exact CPU road rasteriser on 040/060.
10. **H15 — Stretch:** dense car path (cars 33–41 ms per frame), targeting
    16.6 FPS. 25 FPS in the dense pack is not promised.
11. **H16 — Optional:** triple buffering to remove line-256 quantisation.

Expected path under cycle-exact 040, where only the H7 row is measured:

- **After H7:** solo 24.96 FPS (~2.5 ms slack); grid 19.97 FPS.
- **After H9–H11:** solo, normal and grid at 25 FPS (estimated).
- **H13:** margin for the 030.
- **Dense:** needs H15.

In the default profiles, H7 alone gives 24.96 FPS for solo and grid on
030/040/060. B8-PAL cleanup remains separate.

### Evidence and reproduction

- Traces: `tmp/dev/tmp/step5/hi25-profile-040-40-*`
  (gzip-verified `detail.bin.gz`, `hi25-analysis.json`).
- FPS results: `tmp/dev/tmp/step5/c4-q03-h5-fps-*-hi25-*`.
- Tools: `tmp/dev/tools/build_hi25_fixtures.py`, `capture_hi25_profile.py`,
  `analyze_hi25_{profile,calls,irq,blits,blitgaps}.py`,
  `manifest_hi25_profile.py`.
- Emulators: the 040/060 trace hook is in a separate measurement emulator,
  SHA256 `d1c6e976…`. The accepted observer `e411569c…` is unchanged.


## H6 measurement baseline (2026-10-15)

Source HEAD `914e24b` has H5 game code (`25ca4b9`). The unchanged baseline
slave is 264,520 bytes, SHA256
`57900954b6eb18f1691f3ff8f9b51bcb4beb8a6c3456b6d33f1268cc810c9316`.
The local profiles add `030-50-bce`, `040-40-bce` and `060-50-bce` with
the existing CPU options plus `--uae_blitter_cycle_exact=true`.
`030-50-trace` and its BCE variant use 68EC030 because the full-MMU 68030
dispatch loop has no instruction trace. The accepted observer remains
unchanged (`e411569c…`); the existing 040/060 trace observer is `d1c6e976…`.

Each row is 300 complete displayed-buffer intervals after 100 warm-up
presentations, warp off, zero engine errors and no incomplete fixture draws.
Launch: `CUSTOM1=0 CUSTOM2=1 ConfigDelay=0 NoWriteCache`. Normal is the live
demo; solo/grid/dense use the existing Hi25 fixtures. An initial CUSTOM1=1
normal 020 run ended its demo before 300 intervals and was rejected; the
accepted matrix uses the established CUSTOM1=0 scope throughout. Actual
blitter DMA slots were checked to distinguish the two models.

25 FPS means **all 300 intervals are two PAL fields**: mean and p95
40.063774 ms, or 24.960205 FPS. Histogram notation is `fields:count`.

| Profile | Scene | FPS | Mean ms | p95 ms | Interval histogram |
|---|---|---:|---:|---:|---|
| a1200-fast | normal | 15.28176 | 65.43750 | 80.12755 | 3:220, 4:80 |
| a1200-fast | solo | 12.17571 | 82.13074 | 100.15944 | 4:270, 5:30 |
| a1200-fast | grid | 14.59661 | 68.50905 | 80.12755 | 3:178, 4:118, 5:4 |
| a1200-fast | dense | 7.14510 | 139.95612 | 140.22321 | 6:11, 7:282, 8:7 |
| 030-50 | normal | 17.35356 | 57.62506 | 60.09566 | 2:37, 3:263 |
| 030-50 | solo | 21.24273 | 47.07493 | 60.09566 | 2:195, 3:105 |
| 030-50 | grid | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 030-50 | dense | 12.48010 | 80.12755 | 80.12755 | 4:300 |
| 040-40 | normal | 18.26356 | 54.75382 | 60.09566 | 2:80, 3:220 |
| 040-40 | solo | 23.11130 | 43.26888 | 60.09566 | 2:252, 3:48 |
| 040-40 | grid | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 040-40 | dense | 12.48010 | 80.12755 | 80.12755 | 4:300 |
| 060-50 | normal | 18.02181 | 55.48833 | 60.09566 | 2:70, 3:229, 4:1 |
| 060-50 | solo | 23.32729 | 42.86824 | 60.09566 | 2:258, 3:42 |
| 060-50 | grid | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 060-50 | dense | 12.48010 | 80.12755 | 80.12755 | 4:300 |
| 030-50-bce | normal | 17.03768 | 58.69343 | 60.09566 | 2:21, 3:279 |
| 030-50-bce | solo | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 030-50-bce | grid | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 030-50-bce | dense | 9.98408 | 100.15944 | 100.15944 | 5:300 |
| 040-40-bce | normal | 16.65865 | 60.02889 | 60.09566 | 2:2, 3:297, 4:1 |
| 040-40-bce | solo | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 040-40-bce | grid | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 040-40-bce | dense | 9.98408 | 100.15944 | 100.15944 | 5:300 |
| 060-50-bce | normal | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 060-50-bce | solo | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 060-50-bce | grid | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 060-50-bce | dense | 9.98408 | 100.15944 | 100.15944 | 5:300 |

Evidence: `tmp/dev/manifest/render-h6-baseline.json`; `tools/audit_h6.py` verifies all 28 runs.


## H7 accepted: fine-path BLIT ownership (2026-10-15)

H6 is complete and H7 passes the user-reduced emulator acceptance scope.
The final production slave is 264,700 bytes, SHA256
`b6efb0e69f53a7b6e47e1e612c409252a94a8f45514fe9b65c6fa8ea851ed454`. An independent build is byte-identical.
The equal-layout control differs only at file byte 178737 (the immutable
preset); the 68000 and chip-only 020 payloads are byte-identical to H6.
CUSTOM2 remains default-off. The RC2 archive is unchanged; no packaging or
push is included.

### Implementation

`RenderBlit.s` owns only INTENA.BLIT in the fine (020+Fast) payload. It
acquires at epoch start, after resume, and at every `B8Draw` entry. First
acquisition saves the entry bit, including an initially clear bit. Subsequent
draws read INTENAR once and clear any re-enable without replacing that saved
state. The already-owned path uses a byte read of INTENAR's low byte and
borrows no data/address registers; first acquisition saves d0/a0. CCR is
preserved with `move.w ccr`, never privileged `move.w sr`.

Restore writes the saved entry state and clears ownership before the public
reset table clears transient data. Pause, native exit/tow/modal teardown,
overlay unload and production faults use the existing lifecycle hooks and
patch ledger. No new native patch site, DMA allocation or INTREQ write is
introduced. The immutable `FF1FineBlitControl` preset selects equal-layout
acceptance arms; the release-facing CUSTOM2 option remains default-off.

The first candidate failed the strict 020 dense mean gate by one PAL field
over 300 intervals (8.866858 → 8.861611 FPS, unchanged p95), reproduced on
a second pair. Its evidence is retained in `tmp/dev/tmp/h7-v1`. Reducing
only H7's register-save overhead gave a fresh probe of 8.866858 → 8.872111
FPS with unchanged p95. All code-dependent acceptance checks were restarted
for that refined implementation; the first candidate was not accepted.

### BLIT enabler and ownership evidence

The enabler is KickEmu 1.3 graphics.library's `gb_timsrv` CIA-B alarm
callback. It calls `ciab.resource/AbleICR` with mask 4 to disable ALRM,
tests `gb_blthd` at graphics base +$3a, then writes `$8040` to INTENA
and INTREQ when that queue is empty. Its code was verified in live memory.
Logging every INTENA write involving bit 6 from boot through the native
pause/tow/pit/menu/unload/re-entry sequence found one such callback after
the guest Kick reset on each 030/040/060 boot and none on the 020 boot.
Thus the observed `$67EC` versus `$67AC` is a startup alarm-delivery
difference, not a fine-path CPU-selection policy. No later native bit-6
write occurred in those baseline lifecycle runs. This identifies the
observed cause without claiming why every possible boot delivers the alarm.

The native BLIT handler acknowledges the request and returns with BLIT
still enabled when both graphics queues are empty. Racing snapshots show
`gb_blthd` and `gb_bsblthd` (base +$3a/+$42) both zero. Exec interrupt vector
6 consistently identifies the single graphics `gb_bltsrv` node (base +118),
with unchanged code/data through the lifecycle. The static native audit of
118 CODE hunks finds no graphics QBlit/QBSBlit calls; its two apparent
negative-vector matches resolve to Exec FindTask. Dynamic trace checks
complement this bounded evidence; it is not a claim about untested future
workloads.

The separate diagnostic logger (`42c8deb0…`) is used only for boot/lifecycle
INTENA provenance, never for FPS acceptance. The accepted observer is
unmodified. Full evidence is in `tmp/dev/manifest/render-h7-enabler.json`
and `manifest/step5-c4-blit-d1-queue-audit.json` under the local harness.

### Correctness and reduced acceptance scope

At the user's request, the oversized CPU × scene validation matrix was
replaced with representative checks. The final binary passes 100 exact
game-state updates and all recorded private fractions on 020+Fast, plus
30 complete RGB comparisons for each normal/solo/grid/dense scene, with
no masks, crops or pixel tolerance. Its 60-second elapsed error is
0.092576%, below the 0.25% limit. No duplicate final 040 correctness suite
is claimed. The unchanged coarse payloads are verified byte-for-byte.

The first implementation's initial 040-bce normal image capture failed
equality: the existing two-field observer window included B8-PAL's
timing-dependent blue COLOR00 pulse boundary. These rejected captures
are retained. A test-only hold after draw completion lets three PAL wraps
pass with no further CPU draw or palette writes, so the two-field observer
records a stable complete scanout. That method passed all four scene
comparisons on the first implementation and is used for all final 020
complete-frame comparisons. Both arms have the same hold and differ only
at the immutable H7 preset byte. No production palette write was removed
or changed; the hold is absent from state, elapsed, FPS and trace
measurements. Identical transitional RGB fields are not claimed. B8-PAL
remains separate work.

All 20 directed ownership/fault cases pass on 020/030/040/060: both entry
bit states, repeated acquire/restore, re-enable while owned, pending BLIT
completion, CCR preservation, and direct/scheduler/velocity fault exits.
The final 040 native input/lifecycle run passes pause/resume, tow, pit, menu,
overlay reload and race re-entry. INTENA is `$67AC` while owned, returns to
its entry `$67EC` on pause/exit, and is acquired again on resume/re-entry.
All 906 installed patch words are restored. A directed owned native unload
restores the ledger and interrupt state before freeing the overlay, then
returns through the native unloader. CUSTOM2=0 is legacy-exact on the
representative 020+Fast profile with both CUSTOM1 settings; other disabled
profiles were not rerun after the user reduced the matrix.

The rejected first candidate's evidence is retained, as is one 060 test
startup timeout before race entry. Its retry passed. Neither is substituted
for final-binary acceptance. Completed final-binary results are reused only
with matching binary hashes. Human full races and real hardware remain deferred.

### Fresh FPS results

Each result is 300 complete displayed-buffer intervals after 100 warm-up
presentations, warp off, zero engine errors. `control` is the H7 equal-layout
preset control. No control is implied for the candidate-only 030/060 grid
rows; their H6 historical baselines are listed separately above. In
particular, layout/startup differences make the old 020 solo/dense H6
measurements unsuitable as paired H7 controls. The reduced final matrix
does not claim fresh solo/normal/dense measurements on every high-end CPU.

| Profile | Scene | Arm | FPS | Mean ms | p95 ms | Fields:count |
|---|---|---|---:|---:|---:|---|
| a1200-fast | normal | control | 15.23512 | 65.63782 | 80.12755 | 3:217, 4:83 |
| a1200-fast | normal | candidate | 15.26618 | 65.50427 | 80.12755 | 3:219, 4:81 |
| a1200-fast | dense | control | 8.86686 | 112.77952 | 120.19132 | 5:116, 6:179, 7:5 |
| a1200-fast | dense | candidate | 8.87211 | 112.71275 | 120.19132 | 5:120, 6:172, 7:8 |
| 040-40 | solo | control | 23.18285 | 43.13533 | 60.09566 | 2:254, 3:46 |
| 040-40 | solo | candidate | 24.96020 | 40.06377 | 40.06377 | 2:300 |
| 040-40 | grid | control | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 040-40 | grid | candidate | 24.96020 | 40.06377 | 40.06377 | 2:300 |
| 040-40-bce | solo | control | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 040-40-bce | solo | candidate | 24.96020 | 40.06377 | 40.06377 | 2:300 |
| 040-40-bce | grid | control | 16.64014 | 60.09566 | 60.09566 | 3:300 |
| 040-40-bce | grid | candidate | 19.96816 | 50.07972 | 60.09566 | 2:150, 3:150 |
| 030-50 | grid | candidate | 24.96020 | 40.06377 | 40.06377 | 2:300 |
| 060-50 | grid | candidate | 24.96020 | 40.06377 | 40.06377 | 2:300 |
| 030-50-bce | grid | candidate | 19.96816 | 50.07972 | 60.09566 | 2:150, 3:150 |
| 060-50-bce | grid | candidate | 19.96816 | 50.07972 | 60.09566 | 2:150, 3:150 |

020 normal and dense both pass mean/p95 no-regression. Default-model grid
reaches 24.960205 FPS on all three high-end CPUs, with every interval two
fields. Under cycle-exact blitting, grid is 19.968164 FPS on all three:
150 two-field and 150 three-field intervals, mean 50.079718 ms, p95
60.095661 ms. The paired 040 solo result is 24.960205 FPS under both models.

### Residual for H8

Three fresh 30-field candidate traces retain empty QBlit/QBSBlit queues, the
same single graphics BLIT server, no queued-blit calls and no enabled BLIT
observations. All recorded DMA addresses remain in Chip (maximum `$59FB0`).
The EC030 trace contains 1,268,169 instructions, validating that profile.
The accepted observer and separate 040/060 trace observer remain unchanged.

| Cycle-exact profile | Post-wait grid draw, ms | Above estimated 37 ms budget | Above 33 ms margin target |
|---|---:|---:|---:|
| 030-50-trace-bce | 41.39726 | 4.39726 | 8.39726 |
| 040-40-bce | 40.25469 | 3.25469 | 7.25469 |
| 060-50-bce | 40.44585 | 3.44585 | 7.44585 |

Thus H8 starts with **40.25 ms on 040-bce and 40.45 ms on 060-bce**. It
should rank the remaining work needed to remove about 3.3–3.5 ms for the
estimated two-field budget, or 7.3–7.5 ms for margin. H8–H16 are not
implemented here. H12 was subsequently dropped by the user.

### Acceptance evidence

The local audit `tmp/dev/tools/audit_h7_final.py` verifies the final binary
hashes, all retained RGB pixel hashes and state records, FPS/no-regression
results, ownership/fault cases, lifecycle/unload, disabled options and traces.
Its result is `tmp/dev/manifest/render-h7-validation.json`; the reduced run
index is `manifest/render-h7-reduced.json` under the harness. Additional
indices are `render-h7-build-audit.json`, `render-h7-enabler.json` and
`render-h7-traces.json`. Raw traces were gzip-compressed, decompressed hashes
verified, then removed. Archives, fixtures, builds and harness remain ignored.

## H8 — Post-H7 profiling and priority order (2026-10-15)

**Complete; analysis only.** Reanalysed the three accepted H7 30-field,
cycle-exact-blitter grid traces against source `975dace`. Each contains eleven
complete draws. These are the final ownership implementation, not the earlier
IRQ-disable diagnostic. Decompressed trace SHA256 and fixture slave SHA256
match their recorded values on all three profiles. No emulator matrix was
repeated: game code, production binary and RC2 are unchanged.

### Corrected attribution

The old call analyser divided by twelve draw entries, including an unfinished
last draw. H8 accumulates each draw separately and commits its counters only
at the matching B8Draw return; all three complete-draw counts agree with the
stage analyser. It also separates the inline beam wait from the preceding
`FF1RenderPrepareRoad` call. Without that split the 040 report attributed
7.283 ms to preparation, most of it waiting. Preparation actually occupies
about 1.31 ms, outside the post-wait draw budget.

Complete-call totals reconcile with the independent complete-stage totals to
within 0.02 ms (printed values round to 0.001 ms). Calls are inclusive through
the next top-level call, not exclusive instruction timings. A wait charged to
a call may finish a blit started by its predecessor. Do not interpret every
call's wait time as work that deleting that call would save.

| Grid measurement, ms per complete draw | EC030/50 BCE | 040/40 BCE | 060/50 BCE |
|---|---:|---:|---:|
| Post-wait draw | 41.397 | 40.255 | 40.446 |
| Road drawing | 11.323 | 11.131 | 11.258 |
| Background clear `$6b050` | 5.336 | 5.055 | 4.999 |
| `$6b950` | 3.646 | 3.645 | 3.633 |
| Opponent scene `$69bb8` | 5.481 | 5.182 | 5.249 |
| Cockpit/gauges/mirrors: six H13 calls | 11.722 | 11.668 | 11.667 |
| Demo text + final HUD calls | 2.805 | 2.526 | 2.564 |
| Whole-draw WaitBlit spin, including pre-wait work | 32.759 | 31.908 | 32.366 |
| Whole-draw interrupt service | 0.976 | 0.715 | 0.732 |

The call rows and whole-draw categories are overlapping views, not additive
costs. Faster CPU execution alone does not resolve this workload: the 060
post-wait draw is slightly longer than the 040. The H7 safety audit retains
empty graphics queues, no enabled BLIT observations and DMA entirely in Chip.

The DMA census measures about 14.02 ms of blitter activity per 20.03 ms field
on 040/060, with about 30% of slots free. Blitter sequencing and its channel
cycle pattern, rather than a fully saturated bus, remain the main limit.
On 040, the full-window census has 0.8 CD exclusive fills per field, consuming
2.039 ms/field; the largest are 24 words by 103–106 rows and reach 2.96 ms.
These are whole-window observations, not a conversion using eleven complete
draws as the denominator. H9 must identify the road/mirror destinations before
assuming that every fill belongs to its patch scope.

### Ranked next work

1. **H9 — Narrow road-fill spans.** First: the road stage costs 11.1–11.3 ms,
   and the two large full-width fills offer a localized way to reduce actual
   blitter work. Retain the provisional 1.5–3 ms saving estimate, not a measured
   gain. Capture each pre-fill plane, map edge extents and mirror callers,
   then model descending exclusive-fill carry and band boundaries exactly.
   Proceed only when the narrowed result is byte-identical, including edge
   words and pixels outside the proposed span. Keep the coarse payloads
   unchanged in this fine-path series; any all-CPU port is separate scope.
2. **H10 — Background clear.** Second: `$6b050` costs approximately 5 ms/draw.
   Benchmark CPU Chip stores versus the existing blits at the same beam phase
   before choosing CPU-only or concurrent CPU/blitter work. The previous
   2–3 ms saving remains a hypothesis, dependent on memory contention and CPU
   profile. Do not replace the clear merely because cached instructions look
   cheap in the emulator. H9+H10's estimated 3.5–6 ms could meet the two-field
   budget, but does not guarantee it or the 33 ms margin target.
3. **H13 — Cockpit/gauges/mirrors.** Move ahead of H11 if H9+H10 leave the target
   unmet. This group costs 11.67 ms on both 040 and 060. On 040 the individual
   calls are `$6ba18` 2.909, `$6c0d0` 2.166, `$6bbfc` 2.030, `$6adf8` 1.843,
   `$6ae70` 1.523 and `$6af7e` 1.197 ms. Start with the largest proven opaque
   copy opportunity; evaluate small CPU gauge segments separately. Confirm
   source masks and destination dependencies before choosing an implementation.
   The earlier 2–4 ms saving estimate remains unvalidated.
4. **H11 — Overlap text/HUD.** Lower priority than originally proposed. The
   040 text/HUD total of 2.526 ms includes 1.455 ms of waiting; only about
   1.071 ms is CPU work (060: 1.072 ms). Moving the call does not automatically
   remove the earlier blit's completion cost. Treat roughly 1.1 ms as the
   observed CPU work potentially hideable in this grid fixture, before bus
   contention, rather than promising the earlier 1.5–2.3 ms saving. Prove the
   top-region write ordering and measure any additional removed waits.
5. **H12 — Inter-blit latency: dropped by user decision (2026-10-15).**
   No WaitBlit polling shortcut or blitter-priority change is planned.

### Stop rule and scope

The estimated post-wait budget remains about 37 ms: 040/060 need roughly
3.25/3.45 ms less work, or 7.25/7.45 ms to reach the 33 ms margin target.
The decisive gate is still **300 complete intervals all two PAL fields**
(mean = p95 = 40.06377 ms), not a short-trace average below 37 ms.
The retained H7 grid FPS is 19.96816 on all three accelerated BCE profiles,
with 150 two-field and 150 three-field intervals. Therefore H6c's common-scene
25 FPS target is not yet met, and the next implementation is H9.

After each accepted optimization, check that candidate's affected workload and
stop adding optimizations once the H6c targets pass. Preserve the user's reduced,
representative validation scope; do not restore the previous Cartesian test
matrix. Final common-scene success still needs direct normal/solo/grid evidence
on 040/060 BCE, with 030 a should-target and dense/020 no-regression checks.
This H8 analysis makes no new normal, solo or dense performance claim and no
real-hardware claim. It changes no control, lifecycle or simulation behavior,
so repeating their unchanged H7 correctness tests was unnecessary.

Local reproducibility: `tmp/dev/tools/run_h8_analysis.py` verifies and expands
one retained trace at a time, invokes `analyze_h8_calls.py`, checks reconciliation
and removes the temporary raw trace. Results and source hashes are in
`tmp/dev/manifest/render-h8-analysis.json`; per-trace `h8-calls.json` records the
corrected calls. The H7 trace index and original analyses remain intact.

## H9 — Exact road-fill narrowing (accepted, 2026-10-15)

The fine path replaces native `$6abc6` with a bounded, banded version of its
same two descending CD exclusive fills. All native relocation records identify
one caller, the main-road call at `$6b8be`; the mirrors do not use this entry.
The 68000 and chip-only 020 payloads remain byte-identical. CUSTOM2 remains
default-off, and RC2 is unchanged.

### Exact bounds and implementation

The captures revise the original geometry-based estimate: one road plane has
roughly 50 empty lower rows, while the other usually reaches both screen edges.
`RenderFill.s` therefore reads the actual pre-fill Chip words rather than
inferring a potentially unsafe bound from projected endpoints. Each band has
at most 16 rows. It scans right-to-left in longwords, only outside the widest
bound already found in that band, and keeps the left boundary at column zero.
A completely empty band needs no blit. Nonempty bands use the original minterm,
exclusive-fill mode, zero initial carry, masks and 48-byte row stride, with a
narrower width and corresponding descending modulo.

Keeping the left edge is deliberate: skipped right-hand words are all zero,
so carry is still zero when entering the shortened row. Odd-parity rows retain
the native fill all the way to the left edge. Each row resets carry, so band
boundaries do not change the result. No closed-polygon assumption is needed.
Rows outside the native fill range are untouched. Extents outside 1–200 rows
retain the original native routine.

The native WaitBlit synchronizes preceding line writes before any scan.
Scanning a subsequent disjoint band can overlap the preceding fill; register
changes wait for completion, and both plane boundaries and the return are
synchronized. No H12-style WaitBlit shortcut or priority change is included.
The existing cache policy is unchanged; these are reads from the original Chip
DMA planes. Code lives in the public fine payload; no new allocation or
persistent workspace is needed. The immutable equal-layout preset changes one
byte only. The new entry uses the existing patch ledger for restoration.

### Reduced acceptance

- The reference fill model passes on 16 captured pre-fill planes and 450
  directed cases, including zero, dense, sparse, odd-parity and edge-bit rows,
  partial bands and heights 1–200. It compares all 200 rows, including those
  outside the fill. Captured narrowed work is 28,428 versus 39,792 words
  (28.56% fewer); this is a DMA-word reduction, not a whole-frame speedup.
- 100 updates have identical game state and private physics fractions on
  020+Fast. All 30 completed RGB frames in each of normal, solo, grid and
  dense match exactly. The previously accepted test-only scanout hold is used
  in both image arms; production B8-PAL behavior is unchanged.
- The 60-second elapsed check has 0.125890% error,
  below 0.25%. Native 040 pause/resume, tow, pit/menu and fresh-session re-entry
  pass; all 909 owned patch words restore. The H9 entry is
  explicitly verified on takeover and after reload. INTENA ownership/restoration
  remains exact. A deliberately wrong H9 signature exits before its hook is
  installed. Controlled CUSTOM2=0 is exact on 020+Fast with both CUSTOM1 values.
- Matched 040 cycle-exact traces retain empty graphics queues, no BLIT-enabled
  observations and DMA entirely in Chip (highest address `$59fb0`). An independent
  production rebuild is byte-identical. This is the representative reduced
  scope, not a repeated CPU-by-scene qualification matrix.

### Measured performance

300 complete presentation intervals per run, warp off after warm-up. BCE means
cycle-exact blitter. Mean/p95 are milliseconds; histograms count PAL fields per
interval. Controls differ only at the H9 preset. The 060 row is candidate-only,
not a fresh matched A/B; no new 030 or default-blitter claim is made.

| Profile | Scene | Arm | FPS | Mean ms | p95 ms | Interval histogram |
|---|---|---|---:|---:|---:|---|
| a1200-fast | normal | control | 15.25063 | 65.571 | 80.128 | 218 × 3, 82 × 4 |
| a1200-fast | normal | candidate | 15.34439 | 65.170 | 80.128 | 224 × 3, 76 × 4 |
| a1200-fast | dense | control | 8.89847 | 112.379 | 120.191 | 121 × 5, 175 × 6, 4 × 7 |
| a1200-fast | dense | candidate | 8.97849 | 111.377 | 120.191 | 133 × 5, 166 × 6, 1 × 7 |
| 040-40-bce | grid | control | 19.96816 | 50.080 | 60.096 | 150 × 2, 150 × 3 |
| 040-40-bce | grid | candidate | 19.96816 | 50.080 | 60.096 | 150 × 2, 150 × 3 |
| 040-40-bce | dense | control | 12.03868 | 83.066 | 100.159 | 256 × 4, 44 × 5 |
| 040-40-bce | dense | candidate | 12.46971 | 80.194 | 80.128 | 299 × 4, 1 × 5 |
| 060-50-bce | grid | candidate | 19.96816 | 50.080 | 60.096 | 150 × 2, 150 × 3 |

Both 020 workloads and 040 dense pass mean/p95 no-regression. Dense 040 improves
12.03868 → 12.46971 FPS; 040/060 grid remains 19.96816 FPS. The matched 30-field
040 grid trace reduces post-wait draw **40.24848 → 39.90844 ms**, a
**0.34005 ms** saving. Its inclusive road call falls 11.120 → 10.414 ms.
Whole-window CD-fill activity falls about 2.039 → 1.465 ms per field, but the
CPU scan and extra setup consume much of that saving. Per-field DMA and
per-draw call measurements are different denominators and are not additive.
The original 1.5–3 ms whole-frame saving estimate was not achieved.

H6c's 25 FPS target remains unmet: grid still has 150 two-field and 150
three-field intervals. H10 is next, followed by H13/H11 only if needed;
H12 is dropped. Stop further optimizations once the
common-scene two-field gate passes. B8-PAL cleanup, successor packaging, human
full races and real hardware remain separate/deferred work.

Production slave: 265,512 bytes, SHA256
`b313710c295498f9a798728850c4b215d4eb0c412c2dd3cd9e0586baaceb3c5e`.
Local evidence: `tmp/dev/manifest/render-h9-validation.json`, build/model/caller
audits, `render-h9-checks.json`, matched `hi25-profile-040-40-bce-h9-grid-*`
compressed traces and the H9 capture/model/check tools. RC2 SHA256 remains
`cdd0357047f302f1faec3584eafba5af2bfa56720452ab1f7eb1ad806a87c68b`.


## H10 — CPU background clears on 030+ (accepted, 2026-10-15)

H10 replaces the six solid D-only background fills inside `$6b050` with
CPU stores on WHDLoad-detected 030/040/060 + Fast. The native three-plane
loops retain their destinations, colours and geometry: the lower band starts
at row `100-h`, spans `100+h` rows, and sets planes 0/1 to zero and plane 2
to ones; the upper 17-row band starts at row 58 and sets plane 0 to ones and
planes 1/2 to zero. Each row remains 24 words / 48 bytes.

`RenderClear.s` patches only the two BLTSIZE writes at `$6b0e4` and `$6b138`.
Twelve-register MOVEM stores write each complete row. Both wrappers preserve
all CPU registers and reproduce the displaced MOVE's CCR, including X.
Unexpected lower-band heights (zero/1024 or above 200) retain the native
BLTSIZE write. The original ownership, WaitBlit calls and geometry calculations
stay in place; this is not an H1/H12 wait shortcut. No extra DMA allocation,
inter-frame cache, mutable workspace or interrupt/priority policy is added.

The installer reads the existing WHDLoad ATTNFLAGS result through a generated
host-symbol offset (`$8c`: 030/040/060). Guest Exec is not used. 020+Fast keeps
the native clears, and the 68000/chip-only 020 payloads are byte-identical.
The equal-layout control validates the same native signatures and leaves both
writes intact; its only binary difference is `FF1RenderClearControl` at byte
169919. The preset is outside lifecycle reset ranges.
The public patch ledger owns all seven new patch words and restores them on
native exit before re-binding them on reload. CUSTOM2 remains default-off.

### Required CPU-store benchmarks

Before selecting the implementation, three matched grid microbenchmarks ran
at the native clear phase with cycle-exact blitting, 12 traced fields per arm.
The 030 trace uses 68EC030 because the full-MMU loop lacks instruction records.
Both live hook operands were checked before capture. The initial diagnostic
was outside the binding scan and did not install; those results were discarded
and are not performance evidence. The corrected diagnostic produced:

| Profile | Control post-wait ms | CPU-store post-wait ms | Saving ms |
| --- | ---: | ---: | ---: |
| 030-50-trace-bce | 41.03260 | 37.57378 | 3.45882 |
| 040-40-bce | 39.87920 | 36.99321 | 2.88599 |
| 060-50-bce | 39.98553 | 37.49353 | 2.49200 |

The inclusive background call falls from 5.084 to 2.552 ms on EC030,
5.267 to 2.623 ms on 040, and 5.225 to 2.887 ms on 060. CPU Chip-store
transactions and patterns are verified in all three candidate traces.
These short diagnostic traces select CPU-only clears; a concurrent CPU/blitter
variant was not needed or accepted. They are not the final production timing
claim: production adds explicit CCR preservation and the height guard. CPU
instruction/cache charging remains emulator-specific. No hardware speed or
CPU-ranking claim is made.

### Reduced representative acceptance

- 480 native-blitter versus CPU primitive cases pass: all 32 CCR inputs,
  all three plane colours, lower heights 1/17/100/200 and the 17-row upper
  band. Every complete 9,600-byte plane, including untouched pixels, agrees;
  CCR, destination pointer and the D0 size word are checked.
- 040 cycle-exact passes 100 exact state/private-fraction updates and 30
  complete RGB frames each for normal, solo, grid and dense. This CPU carries
  the detailed correctness tests because 020 deliberately does not install H10.
  The accepted H7 three-field test-only scanout hold is retained; production's
  inherited B8-PAL pulse is unchanged, with no pixel masks or timing tolerance.
- 60 simulated seconds on 040 cycle-exact differ from elapsed time by
  0.025883% (gate <=0.25%).
- Actual 040 pause/resume, tow, pit/menu and session re-entry pass; all
  916 owned patch words restore. Both new hooks are verified at takeover
  and after re-entry. A deliberately damaged clear signature aborts before
  either clear hook is installed.
- Controlled CUSTOM2=0 remains legacy-exact on 020+Fast with both CUSTOM1
  settings; static coarse-payload identity covers the unchanged coarse code.
  This keeps the user-reduced representative scope, not a Cartesian matrix.
- The final trace verifies CPU row patterns and actual Chip bus stores,
  with selected words outside their display-fetch intervals. DMA stays in Chip,
  graphics queues remain empty, and BLIT remains disabled during racing.

### Final 300-presentation results

Warp is off during measurement. Each row uses 300 complete intervals and
excludes window boundaries. Histograms are count × PAL fields. Only the 040
and 020 rows are fresh matched production-control pairs; 030 and 060 grid
rows are candidate-only. No new default-blitter result is claimed.

| Profile / scene / arm | FPS | Mean ms | p95 ms | Histogram |
| --- | ---: | ---: | ---: | --- |
| a1200-fast / normal / control | 15.37590 | 65.03686 | 80.12755 | 226 × 3, 74 × 4 |
| a1200-fast / normal / candidate | 15.37590 | 65.03686 | 80.12755 | 226 × 3, 74 × 4 |
| 040-40-bce / grid / control | 19.96816 | 50.07972 | 60.09566 | 150 × 2, 150 × 3 |
| 040-40-bce / grid / candidate | 24.71307 | 40.46441 | 40.06377 | 294 × 2, 6 × 3 |
| 040-40-bce / dense / control | 12.48010 | 80.12755 | 80.12755 | 300 × 4 |
| 040-40-bce / dense / candidate | 12.48010 | 80.12755 | 80.12755 | 300 × 4 |
| 060-50-bce / grid / candidate | 24.87728 | 40.19732 | 40.06377 | 298 × 2, 2 × 3 |
| 030-50-bce / grid / candidate | 24.96020 | 40.06377 | 40.06377 | 300 × 2 |

All paired mean/p95 no-regression gates pass. The 020 pair is identical because
H10 is not installed there. Dense remains within the same four-field budget.
The final matched 30-field 040 grid trace measures post-wait drawing
39.897876 -> 37.154777 ms,
a saving of 2.743100 ms per complete draw.
The native last clear finishes in the next caller's WaitBlit, whereas CPU
clears finish before returning. The whole post-wait draw measurement includes
that boundary; individual call totals must not double-count its saving.
The decisive all-300-two-field target is met by this 030 grid run, but 040 and
060 still have occasional three-field intervals. Normal/solo/grid on 040/060
have not all met H6c. Next is H13, then H11 only if needed; H12 is dropped. Do not add further optimizations once H6c is proven.

The independent rebuild is byte-identical: 266,080 bytes, SHA256
`b4cbad2eb95c8e679a43c0cc6c8ad08065bbf11a0515301aa1ad68baacb23d50`. RC2 SHA256 is unchanged:
`cdd0357047f302f1faec3584eafba5af2bfa56720452ab1f7eb1ad806a87c68b`.
B8-PAL cleanup, successor packaging, human full races and real hardware remain
separate work. No new release qualification or archive is claimed.

Local evidence: `tmp/dev/manifest/render-h10-validation.json`,
`render-h10-microbench.json`, `render-h10-checks.json`,
`render-h10-build-audit.json`, default-off manifests, native primitive/lifecycle/
fault captures and hash-verified compressed traces. The validation index also
records exact source/tool and result hashes.

## H12 withdrawn (2026-10-15)

The user dropped H12: focus on reducing the blits themselves, rather than
inter-blit dispatch or polling delays on fast processors. No H12 code was
implemented. H12 is removed from the remaining work; the old saving estimate
is not a measured result or an acceptance target. H13 continues, followed by
H11 only if the common-scene target remains unmet.


## H13 — Bounded CPU gauge strips (accepted, 2026-10-15)

The accepted H13 change replaces six one-row gauge background operations per
rendered frame on WHDLoad-selected 030/040/060 + Fast. `RenderGauges.s` redirects
the calls at `$6bd66` and `$6bdb6`, each executed for three adjacent rows, to a
bounded CPU bitmap operation. These draw the live 68-pixel and 40-pixel source
patterns into the cockpit bitmap. Gauge calculations, foreground bars, cockpit
cookie-cuts and mirrors retain their native code.

Both call signatures are validated before either operand changes. The original
patch ledger owns the four replacement words and restores them on driving exit;
re-entry binds the new live hunk addresses. The CPU path requires one row, three
planes, a 12-word destination stride, foreground 6/background 0, zero source
coordinates, the two native source patterns, and the cockpit plane table.
Unsigned destination and source-width bounds retain the native operation for
other cases. Source data is read live, including first/last-word masks and all
16 destination shifts. There is no cached image or persistent workspace.

The native OwnBlitter/WaitBlit boundary precedes CPU writes, and the native
conditional DisownBlitter epilogue completes the call. The private primitive
oracle compares complete destination planes and native A6/SP/CCR, and checks
that the CPU path preserves its other input registers. Native scratch-register
outputs are unused at these two call sites. Actual Chip bus writes remain within the cockpit
source planes, with no overlapping display bitplane fetch. DMA stays in Chip;
CPU code remains in public Fast memory. No wait shortcut, priority change or
H12 implementation is included. H12 was dropped separately by user decision.

### Rejected larger cockpit option

The captured cockpit mask has 446 fully opaque, 89 transparent and 149 partial
words in its 12 × 57 source rectangle; its openings and edges prevent treating
the whole image as opaque. A live-mask CPU cookie-cut was tested first, copying
opaque words and blending partial words. It passed 68 native pixel comparisons
across shifts and clipping, but the matched 040BCE short trace regressed from
36.97148 to 40.66361 ms post-wait. It is rejected and absent from production.
The bounded gauge diagnostic subsequently passed 108 native comparisons and
saved 0.68650 ms (37.47383 → 36.78733 ms) in a verified-hook 12-field pair.
Those diagnostics are separate from the final production figures below.

### Final production evidence

- 100 exact game-state updates and private fractions; live new hooks checked.
- 30 complete RGB frames each for normal, solo, grid and dense: all exact.
  The existing test-only scanout hold is retained; no pixels or tolerances change.
- 108 native primitive cases, including every pixel shift,
  exact surrounding pixels, CPU register preservation and native A6/SP/CCR;
  CPU execution confirmed.
- 60 simulated seconds: 0.02588261% elapsed error (gate ≤0.25%).
- Native 040 pause, tow, pit/menu and fresh session; all
  920 ledger words restored, new hooks present
  again after re-entry. Corrupting the second signature leaves both calls native
  and reaches the normal WHDLoad failure route.
- Controlled 020+Fast CUSTOM2=0 exact with both CUSTOM1 settings. The 68000 and
  chip-only 020 payloads remain byte-identical to H10; CUSTOM2 remains default-off.
- Independent production rebuild byte-identical: 267064 bytes,
  SHA256 `8b45d6a893ea3b29f3543e66147c3fcb419883c67cbdbfb15d981fe25078f1fd`. The equal-layout control differs only in
  immutable `FF1RenderGaugeControl`; no allocation or reset-state addition.
- Matched 30-field 040BCE grid traces: post-wait draw cost
  **37.327016 → 37.141537 ms**, saving **0.185479 ms**. All trace costs retained.

Warp is disabled for every 300-complete-interval measurement. These are emulator
results, not hardware measurements. As in H10's reduced scope, 030/060 grid
runs are candidate confirmations; fresh matched pairs cover 040 grid/dense and
020 normal. No new default-blitter matrix or release archive is claimed.

| Profile / scene / arm | FPS | Mean ms | p95 ms | Interval histogram (fields) |
| --- | ---: | ---: | ---: | --- |
| a1200-fast / normal / control | 15.37590 | 65.03686 | 80.12755 | 226 × 3, 74 × 4 |
| a1200-fast / normal / candidate | 15.37590 | 65.03686 | 80.12755 | 226 × 3, 74 × 4 |
| 040-40-bce / grid / control | 24.67236 | 40.53118 | 40.06377 | 293 × 2, 7 × 3 |
| 040-40-bce / grid / candidate | 24.75392 | 40.39764 | 40.06377 | 295 × 2, 5 × 3 |
| 040-40-bce / dense / control | 12.48010 | 80.12755 | 80.12755 | 300 × 4 |
| 040-40-bce / dense / candidate | 12.48010 | 80.12755 | 80.12755 | 300 × 4 |
| 060-50-bce / grid / candidate | 24.91867 | 40.13055 | 40.06377 | 299 × 2, 1 × 3 |
| 030-50-bce / grid / candidate | 24.96020 | 40.06377 | 40.06377 | 300 × 2 |

H13's earlier 2–4 ms estimate was not achieved. The small accepted operation
saves measured work, but does not establish the all-300-two-field H6c target
for every common scene. H11 remains the next planned option if that target is
pursued; H12 is dropped. Human full-race playtesting and real hardware remain
deferred. B8-PAL cleanup, packaging and the RC2 archive are unchanged.

Local evidence: `tmp/dev/manifest/render-h13-validation.json`,
`render-h13-microbench.json`, `render-h13-build-audit.json`,
`render-h13-diagnostics.json` and `render-h13-capture-archive.json`.
Completed large captures are hash-verified and compressed; no rejected cockpit
kernel or test counter is part of the production source.

## H11 — Prepare clock glyphs during drawing (accepted, 2026-10-16)

H11 prepares the seven session-clock glyphs after the sky blit has been started,
using 56 bytes of public Fast workspace. At the original final HUD point, it
draws the native flag, waits for completion and copies the prepared live-font
bytes into the existing three Chip screen planes. All screen writers retain
their original order, including the flag that overlaps the first clock glyph.
Clock state is updated outside the synchronous draw; font and clock setup do
not change between preparation and publication. Both pointer views retain H3's
back-buffer aliasing. No DMA accesses the new workspace.

The path is limited to WHDLoad-selected 030/040/060 + Fast, with the existing
fine HUD enabled, native clock position (32,3), foreground 7/background 0,
a valid font pointer and bounded font indices/row width. Other layouts and
colours use the existing renderer. The workspace is rebuilt each draw and
belongs to the existing lifecycle reset ranges; its immutable A/B control is
excluded from reset. There are no new native patches, wait shortcuts,
interrupt/priority changes or early screen writes. H12 remains dropped.

### Choice and measured saving

The proposed early screen writes were evaluated first. A last-wheel placement
saved only 0.098 ms diagnostically and its guarded version regressed by 0.027 ms;
it is absent from production. Moving clock writes next to the sky saved
0.651 ms in a diagnostic, but would require preserving dependencies against
all subsequent screen writers. The accepted Fast preparation keeps those
writers in native order. Diagnostic figures are not production gains.

The final matched 30-field 040BCE grid traces measure post-wait draw cost
**37.131791 → 36.814138 ms**, saving **0.317653 ms (0.86%)**. All recorded
trace costs are retained. This is below the original H11 estimate; it does not
establish the common-scene all-two-field H6c target.

### Acceptance evidence

- 100 exact game-state updates and private fractions.
- 30 complete RGB frames each for normal, solo, grid and dense: all exact.
- 47 native clock bitmap comparisons, including all 28 font columns,
  foreground/background alternatives and position fallbacks. Each compares
  all three complete 9,600-byte planes, including surrounding pixels.
- Trace audit: 840 prepared live-font bytes and 2,520 exact screen-byte stores;
  all preparation reads overlap an active blit. Workspace is Fast; screen writes are bounded to the seven native clock columns
  in rows 24–31, and DMA stays in Chip.
- 60 simulated seconds: 0.02588261% elapsed error (gate ≤0.25%).
- Native 040 pause, tow, pit/menu and fresh session pass; all
  920 patch-ledger words restored. Clock-ready state is clear at lifecycle boundaries.
- Faults injected after preparation restore both possible entry BLIT-enable
  states. No DMA can reference the prepared private bytes.
- Controlled 020+Fast CUSTOM2=0 is exact with both CUSTOM1 settings. The
  68000 and chip-only 020 payloads remain byte-identical to H13; CUSTOM2 stays default-off.
- Independent production rebuild byte-identical: 267,960 bytes,
  SHA256 `84783350ad9b1b5a23d3ac28862e53fbb0fb9cc6fdf553edb6289afcbe8bcb26`. Equal-layout control differs at only
  the immutable `FF1RenderOverlapControl` preset byte.

| Profile / scene / arm | FPS | Mean ms | p95 ms | Interval histogram (fields) |
| --- | ---: | ---: | ---: | --- |
| a1200-fast / normal / control | 15.39170 | 64.97009 | 80.12755 | 227 × 3, 73 × 4 |
| a1200-fast / normal / candidate | 15.39170 | 64.97009 | 80.12755 | 227 × 3, 73 × 4 |
| 040-40-bce / grid / control | 24.71307 | 40.46441 | 40.06377 | 294 × 2, 6 × 3 |
| 040-40-bce / grid / candidate | 24.91867 | 40.13055 | 40.06377 | 299 × 2, 1 × 3 |
| 040-40-bce / dense / control | 12.48010 | 80.12755 | 80.12755 | 300 × 4 |
| 040-40-bce / dense / candidate | 12.48010 | 80.12755 | 80.12755 | 300 × 4 |
| 060-50-bce / grid / candidate | 24.96020 | 40.06377 | 40.06377 | 300 × 2 |
| 030-50-bce / grid / candidate | 24.96020 | 40.06377 | 40.06377 | 300 × 2 |

The reduced representative scope follows H13: matched 040 grid/dense and 020
normal, plus candidate-only 030/060 grid confirmations, all with 300 complete
presentation intervals and warp disabled. BCE denotes cycle-exact blitting.
These are emulator measurements, not hardware results. No expanded Cartesian
matrix or new release qualification is claimed.

H6c common-scene confirmation remains separate, before deciding whether any
optional H14–H16 work is justified. Stop adding optimizations if its targets
pass. B8-PAL cleanup and successor packaging remain separate; the RC2 and H13
preinstalled archives are unchanged. Human full races and real hardware testing
remain deferred.

Local evidence: `tmp/dev/manifest/render-h11-validation.json`,
`render-h11-v2-checks.json`, `render-h11-build-audit.json`,
`render-h11-source-audit.json`, `render-h11-diagnostics.json` and
`render-h11-capture-archive.json`. Completed large captures are hash-verified
and compressed. Rejected screen-reordering variants and test-only fixtures are
absent from production.

## H6c — Common-scene confirmation (2026-10-16)

During this measurement the user requested a realistic goal of 95% of frames
holding 25 FPS. The revised gate is **at least 285 of 300 complete presentation
intervals at two PAL fields**, with the remaining intervals no longer than
three fields. This means p95 = 40.06377 ms and maximum ≤60.09566 ms; it does
not mean a 25 FPS average. Required scenes are normal, solo and grid on
040/060 with cycle-exact blitting; 030 remains a secondary target. Dense retains
its same-workload no-regression gate. The original all-300-two-field result is
preserved in the evidence rather than relabelled as passed.

Measured source: H11 commit `95ba29d3bed5ba48e742e9b663cbcc5794439d1a`.
No game code or build layout changed. Production SHA256:
`84783350ad9b1b5a23d3ac28862e53fbb0fb9cc6fdf553edb6289afcbe8bcb26`.
Six fresh normal/solo measurements complete the missing evidence; the three
same-source H11 grid measurements are retained. Each run uses 300 complete
intervals after 100 warm-up presentations, with warp disabled. Normal is the
production demo; solo/grid are the established deterministic rendering fixtures.
Profiles use 2 MiB Chip and 8 MiB Fast, calibrated CPU timing and cycle-exact
blitting. These are emulator observations, not hardware guarantees or statistical
claims about every track and every possible gameplay scene.

| Profile / scene | FPS | Mean ms | p95 ms | Two-field share | Histogram (fields) |
| --- | ---: | ---: | ---: | ---: | --- |
| 040-40-bce / normal | 24.51084 | 40.79828 | 40.06377 | 96.33% | 289 × 2, 11 × 3 |
| 040-40-bce / solo | 24.96020 | 40.06377 | 40.06377 | 100.00% | 300 × 2 |
| 040-40-bce / grid | 24.91867 | 40.13055 | 40.06377 | 99.67% | 299 × 2, 1 × 3 |
| 060-50-bce / normal | 24.55102 | 40.73150 | 40.06377 | 96.67% | 290 × 2, 10 × 3 |
| 060-50-bce / solo | 24.96020 | 40.06377 | 40.06377 | 100.00% | 300 × 2 |
| 060-50-bce / grid | 24.96020 | 40.06377 | 40.06377 | 100.00% | 300 × 2 |
| 030-50-bce / normal | 24.55102 | 40.73150 | 40.06377 | 96.67% | 290 × 2, 10 × 3 |
| 030-50-bce / solo | 24.96020 | 40.06377 | 40.06377 | 100.00% | 300 × 2 |
| 030-50-bce / grid | 24.96020 | 40.06377 | 40.06377 | 100.00% | 300 × 2 |

**H6c passes the revised gate on all nine common-scene measurements.**
The strict original gate remains unmet. The representative H11 dense pair is
unchanged at 12.48010 FPS (300 four-field intervals), and the 020+Fast normal
pair is unchanged at 15.39170 FPS. Those matched checks are retained without
expanding the test matrix. Existing H11 correctness and lifecycle acceptance
continues to apply because this step changes no game code.

The common-scene stopping rule is satisfied: do not add H14 or H16 to reach
this target. H15 remains a separate optional dense-scene stretch goal, not a
condition of H6c completion. H12 stays dropped. B8-PAL cleanup, successor
packaging/qualification, deferred human full races and real hardware testing
remain separate. Neither preinstalled archive is rebuilt here.

Local evidence: `tmp/dev/manifest/render-h6c-validation.json`; six fresh captures
under `tmp/dev/tmp/step5/*-h6c-*`, plus the linked H11 results. Large memory
captures are compressed with byte-hash verification; compact timing records remain.

## B8-PAL — Remove the diagnostic palette pulse (2026-10-16)

B8-PAL is complete. The shared performance drawing adapter no longer writes
`D1.w` to `COLOR00` after repairing the screen pointers. This inherited diagnostic
write could turn colour zero blue between the CPU write and the next copper
palette load; its timing-dependent boundary explained earlier transitional RGB
differences. The cleanup removes the write rather than masking pixels or
changing the real palette. It applies to 68000, chip-only 020 and Fast-memory
performance paths. The preceding `EXT.L D1` already supplies identical CCR
flags for every 16-bit input; no replacement instruction or test switch remains.

The historical host `.patch` write is deliberately retained for CUSTOM2=0
legacy-exact behavior. That source is unchanged. The shared adapter is used
only by the opt-in performance paths; CUSTOM2 remains default-off.

Focused checks passed:

- All three compiled payloads remove exactly the six-byte write at the audited
  screen-pointer repair site. Exhaustive 65,536-word flag equivalence passes.
- 040BCE: 100 game-state updates and private fractions match H11 exactly.
- 30 complete RGB frames each for normal and grid match H11 exactly, with no
  pixel masks or palette edits. These stable scanouts are separate from the
  transitional-field diagnostic identified in H3.
- Six traced 040BCE grid fields show the draw site executing with no CPU
  palette bus writes versus three in the retained H11 trace. All 54 copper
  palette events match exactly, including field slots. Queue/interrupt and
  Chip-DMA checks pass.
- 60 simulated seconds: elapsed error **0.02588261%**, below 0.25%.
- 300 040BCE grid intervals: **24.96020 FPS**, mean **40.06377 ms**,
  p95 **40.06377 ms**; histogram **{2: 300}**
  in PAL fields. The revised H6c 95%/three-field maximum gate passes.
- Independent build is byte-identical: **267,940 bytes**, SHA256
  `5db5a4c4fb42360578a38aa61c5cdcb3c7524fb4c5bed948f51d305050e1663e`.

This is a palette cleanup, not a claimed speed optimization. No native patch,
simulation, lifecycle, DMA resource, real palette or buffer ownership logic was
changed. The reduced scope does not claim a fresh coarse-path, lifecycle or
CUSTOM2=0 runtime matrix; host source identity and the compiled-site audit
cover the unchanged code contracts. Successor packaging/qualification remains
separate. RC2 and H13 archives are unchanged; human full races and real hardware
testing remain deferred. Earlier B8-PAL limitations describe historical builds.

Local evidence: `tmp/dev/manifest/b8-pal-validation.json`,
`b8-pal-source-audit.json`, `b8-pal-trace-audit.json` and their linked captures.
