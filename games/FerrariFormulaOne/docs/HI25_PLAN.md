# High-end 25 FPS: profile and work plan (2026-10-15)

Goal: on 030/040/060 + Fast, present a new frame every two PAL fields
(40.06 ms, 24.96 FPS) in the normal, solo (no opponents drawn) and starting-grid
scenes; improve the dense pack without regression. This continues the H-series in
`docs/RENDERING_PLAN.md` (H1–H5 closed); IDs start at H6.
The current source is HEAD 25ca4b9 (264,520-byte slave). Nothing here changes
game code; all builds below are diagnostic fixtures.

## Why it is stuck at 16.6 FPS

The fine loop is: tick(s) -> `B8Draw` publishes the previous frame (LoadView),
prepares the road, waits for beam line 256 (or a passed field), then clears and
draws the back buffer. A frame shows every two fields only if the time from one
line-256 release to the next draw's wait check stays under 40.06 ms:
post-wait draw + ticks (~1.6–1.8 ms on 040) + publish/road prep (1.3 ms).
**So the post-wait draw must be <= ~37 ms; aim for <= 33 ms to have margin.**

On the 040 the CPU is not the limit. Post-wait drawing is mostly the CPU
spinning in `gfx_WaitBlit` while the blitter runs, plus interrupt service.
Simulation ticks are cheap (0.8 ms each).

## Short profile (040/40, 30 traced PAL fields after 100 warm-up draws)

Fixtures: `normal` = native demo; `grid`/`dense` = H5 fixed-pose fixtures (7
opponents); `solo` = the dense pose with all seven per-car draw calls counted and
returned before any sprite work (new: `tools/build_hi25_fixtures.py`). "default"
= the accelerated profiles used for H2–H5 acceptance; "cycle-exact" adds
`--uae_blitter_cycle_exact=true` (see M-1 below). ms per drawn frame:

| Scene | Blitter model | Post-wait draw | WaitBlit spin | BLIT IRQ | CPU work | Presentation |
|---|---|---:|---:|---:|---:|---|
| solo | default | 37.6 | 24.0 | 9.8 | 5.1 | 23.11 FPS (252×2, 48×3 fields) |
| normal | default | 41.2 | 26.0 | 11.1 | 5.5 | 18.26 FPS (H5) |
| grid | default | 44.3 | 28.4 | 11.6 | 5.7 | 16.64 FPS (all 3 fields) |
| dense | default | 71.7 | 55.5 | 11.8 | 5.8 | 12.48 FPS (all 4 fields) |
| solo | cycle-exact | 42.8 | 26.4 | 9.9 | 7.8 | 16.64 FPS (all 3 fields) |
| grid | cycle-exact | 50.0 | 31.0 | 11.6 | 8.7 | 16.64 FPS (all 3 fields) |
| dense | cycle-exact | 85.2 | 60.2 | 12.2 | 14.1 | 5 fields in trace (~10 FPS) |

Stage costs (default model, ms/draw) for solo → grid → dense: road 13.5/13.4/13.5,
cars (`$69bb8`) 0.1/6.1/33.2, clear 4.9, `$6b950` 3.0, cockpit/HUD/mirrors/text
14.3–15.3, final 1.8–2.2. Under the cycle-exact model with BLIT IRQ off, grid is:
road 10.2, clear 4.7, cars 4.7, `$6b950` 3.3, `$6ba18` 2.7, `$6c0d0` 2.0,
`$6bbfc` (gauges) 1.9, `$6adf8` 1.7, demo text 1.4, mirrors 2.5 + 0.7, HUD 0.9.

### Finding 1: empty BLIT interrupts cost ~25% of every draw on 030+

INTENA is `$67EC` on 040 (BLIT enabled); the H5 020+Fast trace had `$67AC`.
The H5 audit conclusion ("BLIT already disabled on the fine path") therefore
holds only for that 020 trace. On 040 the level-3 handler is entered ~100–120
times per field, 99% for BLIT, about 37 µs each including WHDLoad's VBR glue
(`$9eff00`) and the Kick 1.3 dispatcher. The blitter is idle during each one.
No `$8040` write occurs inside the windows; it is enabled earlier.

Diagnostic what-if (fixture writes INTENA `$0040` before every draw; no ownership
or restore handling), 300 complete presentations, zero engine errors:

| CPU | Scene | Blitter model | Current | BLIT IRQ off |
|---|---|---|---:|---:|
| 040/40 | solo | default | 23.11 FPS | **24.96 FPS (all 2 fields)** |
| 040/40 | grid | default | 16.64 | **24.96 (all 2 fields)** |
| 030/50 | grid | default | 16.64 (H5) | **24.96 (all 2 fields)** |
| 060/50 | grid | default | 16.64 (H5) | **24.96 (all 2 fields)** |
| 040/40 | grid | cycle-exact | 16.64 | 19.97 (150×2, 150×3) |
| 040/40 | solo | cycle-exact | 16.64 (all 3 fields) | **24.96 (all 2 fields)** |

Traces: post-wait draw falls 37.6 -> 28.4 (solo) and 44.3 -> 33.5 ms (grid)
in the default model; 42.8 -> 34.4 and 50.0 -> 40.2 ms in the cycle-exact model.

### Finding 2: the accelerated profiles run an approximate blitter

`uae_cpu_cycle_exact=true` sets CPU/memory cycle-exactness but not
`blitter_cycle_exact`; on 030/040/060 the blitter runs in UAE's approximate
mode (no slot stealing, no blitter DMA records). Enabling it adds 5–6 ms per
frame (solo 37.6 -> 42.8, grid 44.3 -> 50.0) and moves solo from mostly two to
three fields. H2–H5 accelerated FPS were therefore optimistic. Real hardware is
closer to the cycle-exact model; physical testing remains deferred.

### Finding 3: what the blitter spends its time on (grid, cycle-exact, IRQ off)

Blitter busy 14.0 of 20.0 ms per field; 31% of bus slots stay free, so the bus
is not saturated: the blitter's own cycle pattern is the limit. Per field:

| Blit type | Count | ms | Notes |
|---|---:|---:|---|
| ABCD cookie-cut | 13.3 | 3.78 | cars, cockpit |
| D-only fill | 3.6 | 2.73 | `$6b050` background bands, `$6b950` |
| BCD | 36.9 | 2.63 | mostly 1-row spans (road/kerbs, mirrors) |
| CD exclusive fill | 0.8 | 2.04 | **full-width 24 words × 103 rows, 2.5–2.9 ms each** |
| line | 49.2 | 1.43 | road edges |
| ABD | 9.9 | 1.38 | masks |

Short gaps between consecutive blits (CPU detects completion, computes, writes
registers) are typically 9–22 µs and total 1.9 ms per field.

## Measurement caveats (M-1…M-4)

- M-1: use cycle-exact blitter profiles for acceptance from now on; keep the
  default profiles for continuity with H2–H5.
- M-2: 040/060 instruction costs come from a measurement emulator copy with the
  barto hook added to `m68k_run_3ce` (`tmp/step5-frame-observer-040prof-build`,
  SHA256 `d1c6e976…`; the accepted observer `e411569c…` is unchanged). Cached
  040 instructions cost almost nothing in UAE; time is chip/blitter waiting.
- M-3: the 030 profile uses the full-MMU 68030 loop, which is not instrumented.
  Trace 030 with a 68EC030 profile or instrument `m68k_run_mmu030`.
- M-4: CPU-side Chip write/read speeds assumed by H10/H11/H14/H15 must be
  micro-benchmarked per CPU (H5 method) and are emulator figures until physical
  hardware testing.

## Work order

One switchable equal-layout change per commit, re-profile after each accepted
change (H-series rules). Keep CUSTOM2=0 legacy-exact, the 68000/chip-only
payloads byte-identical, Chip DMA ownership and the 20 ms player / 100 ms
opponent design. Gates for every change: 100-update exact state/private
fractions, 30 complete RGB frames each for normal/solo/grid/dense, 60-second
elapsed (<=0.25%), four-profile CUSTOM2=0, native controls and pause/tow/pit/
menu/re-entry/fault/INTENA restoration; 300-presentation FPS on 020+Fast
(no regression) and 030/040/060 in both blitter models.

**H6 — Measurement baseline (no game code).**
- H6a: Add `030-50-bce`, `040-40-bce`, `060-50-bce` profiles
  (`--uae_blitter_cycle_exact=true`). Add a 68EC030 trace profile (M-3).
- H6b: Adopt the solo fixture, the 040/060 measurement emulator and the
  `analyze_hi25_*` tools. Record fresh 300-presentation baselines for
  normal/solo/grid/dense on 030/040/060 × both blitter models, plus 020+Fast.
- H6c: Fix the target: "25 FPS" means all 300 complete intervals are two
  fields (mean = p95 = 40.06 ms). Targets: normal/solo/grid on 040-bce and
  060-bce (must), 030-bce (should); dense must not regress.

**H7 — Fine-path BLIT interrupt ownership (port of C4 `FF1C4BlitAcquire/Restore`).**
- H7a: Find the enabler. Watch INTENA writes with bit 6 from boot through race
  entry, overlay reload, pit, menu and re-entry on 020+Fast/030/040/060. Explain
  `$67AC` (020) vs `$67EC` (040). Prove the gfx QBlit/QBSBlit queues stay empty
  during racing and that no other BLIT server exists.
- H7b: Own it on the fine path: acquire at epoch start and on resume, re-check
  at each `B8Draw` entry (one INTENAR read covers any re-enable), restore on
  pause/tow/pit/menu/exit/fault/unload through the public lifecycle and ledger.
- H7c: Full gates. Expected from the what-if: 030/040/060 grid and solo reach
  24.96 FPS in the default model; cycle-exact solo 24.96 (~2.5 ms slack),
  cycle-exact grid 19.97. Record the H5 IRQ-audit correction in RENDERING_PLAN.md.

**H8 — Re-profile after H7** on 040-bce and 060-bce (and the 030 trace
profile). Rank H9–H13 by measured residual; stop when H6c targets pass.

**H9 — Exact road-fill narrowing (fine path; see H8 scope and H9 closure).** The two full-width CD exclusive
fills (24 words × ~103 rows) cost 2.5–2.9 ms each. Fill mode resets the carry
per row and the planes are zero outside the edge pixels in that region, so a fill
limited to the word span between each band's outermost edge pixels gives the
same result. Split it into a few bands from the edge extents just drawn. Prove it
with a model on captured pre-fill planes, then frames; check whether the mirrors
use the same fill. Expected −1.5 to −3 ms per frame.

**H10 — CPU background fills on 030+.** Replace or share `$6b050`'s six D-only
fills (~4.7 ms per frame cycle-exact; they start just after line 256, when there
is little bitplane DMA) with CPU longword stores. Optionally the CPU fills one
plane while the blitter fills the others. Gate on per-CPU micro-benchmarks
(M-4). Expected −2 to −3 ms.

**H11 — Overlap top-region text/HUD with long blits.** The flag, clock and demo
label lie in the uncleared rows above the backdrop band. Prove no later writer
touches them (both pointer views, as H3/H4 did), then draw them with the existing
CPU glyph code right after starting a long bottom-region blit, not at the end.
Expected −1.5 to −2.3 ms (text 1.4 + HUD 0.9 cycle-exact).

**H12 — Inter-blit latency: dropped by user decision (2026-10-15).**
No implementation; no polling-delay or priority changes are planned.

**H13 — Cockpit, gauges and mirrors.** Identify `$6ba18`, `$6c0d0`, `$6adf8`
(large cookie-cuts), `$6bbfc` (gauges: many small BCD/ABD) and the mirrors
`$6ae70`/`$6af7e` (~10 ms per frame together, cycle-exact). Exact options:
opaque word runs as A→D copies instead of ABCD; CPU drawing for small bounded
gauge segments (H5 method). Expected −2 to −4 ms.

**H14 — Optional, large: CPU road rasteriser for 040/060.** Port the blitter line,
exclusive-fill and span semantics bit-exactly to Fast RAM, then write the changed
words to Chip. It would replace lines + spans + fills (~6 ms of blitter time per
field, including mirrors) with an estimated 3–4 ms of CPU time per frame. Only
if H9–H13 leave grid/normal short, or for dense.

**H15 — Stretch: dense car path.** Cars cost 33 ms (default) / 41 ms (cycle-exact)
per frame. On 040/060, cookie-cut the cars with the CPU from Fast-RAM
colour-expanded images, or cache expansions to drop the mask/colour blits.
Target: dense >= 16.6 FPS (3 fields) on 040/060-bce. 25 FPS for dense is not
promised.

**H16 — Optional: triple buffering.** This removes the line-256 quantisation: a
45 ms frame gives ~22 FPS instead of 16.6–20. It needs a third Chip buffer and
top-region HUD writes to every buffer. Only if common scenes stay just above
the two-field budget after H7–H13.

## Expected path (cycle-exact 040, estimates except where marked measured)

| After | solo | normal | grid | dense |
|---|---|---|---|---|
| today | 16.6 (measured) | ~3 fields | 16.6 (measured) | ~10 |
| H7 | 24.96, ~2.5 ms slack (measured what-if) | ~2–3 fields | 20.0 (measured what-if) | ~12.5 |
| H7+H9–H11 (−5 to −8 ms) | 25 | 25 | 25 (post-wait ~33–35 ms) | ~12.5–16.6 |
| +H13 | margin | margin | margin, 030 likely | 16.6 needs H15 (and/or H14) |

In the default-blitter profiles, H7 alone already gives 24.96 FPS for solo and
grid on 030/040/060 (measured). B8-PAL cleanup remains separate.

## Evidence (ignored harness)

- Traces/analyses: `tmp/step5/hi25-profile-040-40-{solo,grid,dense,normal}`,
  `-{solo,grid}-nbi`, `-{solo,grid,dense}-bce`, `-{solo,grid}-nbi-bce`
  (`hi25-analysis.json`, `hi25-calls.json`).
- FPS: `tmp/step5/c4-q03-h5-fps-{040-40,030-50,060-50}-hi25-*`.
- Tools: `tools/build_hi25_fixtures.py`, `capture_hi25_profile.py`,
  `analyze_hi25_profile.py`, `analyze_hi25_calls.py`, `analyze_hi25_irq.py`,
  `analyze_hi25_blits.py`, `analyze_hi25_blitgaps.py`.
- Index: `manifest/hi25-profile.json`.

## H6/H7 closure

H6 is complete; H7 is accepted in the user-reduced emulator scope. See the
H7 section of `docs/RENDERING_PLAN.md` and
`manifest/render-h7-validation.json` for the final binary, precise scope,
fresh FPS/histograms and enabler finding. H8 is next: post-wait grid costs
40.25469 ms on040-bce and40.44585 ms on060-bce. H12 is dropped.

## H8 closure

H8 is complete as analysis only. See the H8 section of the tracked
RENDERING_PLAN.md and manifest/render-h8-analysis.json. Reused the three
hash-verified final H7 BCE grid traces; corrected complete-call normalization
and separated beam waiting from road preparation. Next order: H9, H10, H13,
H11 if targets remain unmet; H12 is dropped. H11's
previous saving estimate is not supported by the CPU-work breakdown. No game
changes or repeated emulator matrix. The reduced representative scope persists.

## H9 closure

H9 passed the reduced representative gates. Exact right-edge 16-row bands
and empty-band elision avoid any polygon/parity assumption. Matched 040-bce
grid post-wait40.24848 ->39.90844ms; dense12.03868 ->12.46971FPS; grid remains
19.96816FPS on040/060. The1.5–3ms estimate was not met. 020 normal/dense do not
regress. See tracked RENDERING_PLAN.md and manifest/render-h9-validation.json.
Next H10; H12 is dropped. RC2 unchanged.

## H10 closure

CPU background clears passed per-CPU microbenchmarks and reduced production gates.
040BCE grid19.96816 ->24.71307 FPS;030BCE24.96020 and060BCE24.87728 candidate-only.
040BCE dense12.48010 unchanged;020Fast15.37590 identical. Post-wait040 saving
2.743100 ms. See render-h10-validation.json and tracked RENDERING_PLAN.md.
Next H13, then H11 if needed;H12 is dropped. Common-scene H6c remains open.

## H13 closure

Accepted bounded CPU gauge strips on030/040/060+Fast; larger cockpit CPU copy
rejected after regression. Reduced gates passed; matched040BCE post-wait
37.327016->37.141537ms. See render-h13-validation.json and tracked RENDERING_PLAN.md.
H6c remains open; nextH11 if pursued. H12 dropped;RC2 unchanged.

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

Local evidence: `tmp/manifest/render-h11-validation.json`,
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

Local evidence: `tmp/manifest/render-h6c-validation.json`; six fresh captures
under `tmp/step5/*-h6c-*`, plus the linked H11 results. Large memory
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

Local evidence: `tmp/manifest/b8-pal-validation.json`,
`b8-pal-source-audit.json`, `b8-pal-trace-audit.json` and their linked captures.
