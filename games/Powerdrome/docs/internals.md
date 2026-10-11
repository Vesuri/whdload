# Powerdrome internals

Project status: completion-plan Phase D is complete. Work stopped before Phase E.
See the [current handoff](open-work.md) for completed checks, open gates and resume priorities.

## Current measurements

The complete B2 matrix contains 60 baseline captures, 14 phase captures and three
8 MHz sanity captures. All fps figures use uninstrumented builds, 500 PAL fields from `$bc7c`, and
complete first-to-last driving presentation intervals. These are end-to-end route
rates: changing timing also changes motion, so they are not fixed-scene opcode
speedups. `native` disables C1/C3;
`fast` enables C1; `full` enables C1/C3 with `TIMING_FULL=1`. Cache labels are WHDLoad
options. Machines M1–M7 are defined in the completion plan. C1 falls back to native
on M1/M3 because there is no real fast RAM.

Phase columns use separate `VERIFY_PHASE` captures of the full configuration.
The pairs are mean/p95 milliseconds: W world, R render excluding nested work,
V VBL handshake wait, C chip copy, H HUD, T timer display, P presentation, O other.
Instrumented fps is not substituted for the baseline. Phase averages use all
complete `$8056` presentation intervals, including incident presentations, while
driving fps and its histogram use `$bc7c`. Their interval counts can differ.

| Machine | Cache | Route | Configuration | Intervals/fields | fps | Fields 1/2/3+ | Phase mean/p95 ms (W/R/V/C/H/T/P/O) |
| --- | --- | --- | --- | ---: | ---: | --- | --- |
| M1 | NoCache | practice | native | 104/456 | 11.404 | 0/0/104 | — |
| M1 | NoCache | practice | fast | 104/456 | 11.404 | 0/0/104 | — |
| M1 | NoCache | practice | full | 99/473 | 10.465 | 0/0/99 | — |
| M1 | NoCache | race | native | 113/492 | 11.484 | 0/0/113 | — |
| M1 | NoCache | race | fast | 113/492 | 11.484 | 0/0/113 | — |
| M1 | NoCache | race | full | 104/485 | 10.722 | 0/0/104 | — |
| M2 | NoCache | practice | native | 106/468 | 11.325 | 0/0/106 | — |
| M2 | NoCache | practice | fast | 87/465 | 9.355 | 0/0/87 | — |
| M2 | NoCache | practice | full | 81/465 | 8.710 | 0/0/81 | — |
| M2 | NoCache | race | native | 114/495 | 11.515 | 0/0/114 | — |
| M2 | NoCache | race | fast | 94/490 | 9.592 | 0/0/94 | — |
| M2 | NoCache | race | full | 85/484 | 8.781 | 0/0/85 | — |
| M3 | NoCache | practice | native | 153/496 | 15.423 | 0/20/133 | — |
| M3 | NoCache | practice | fast | 153/497 | 15.392 | 0/20/133 | — |
| M3 | NoCache | practice | full | 144/494 | 14.575 | 0/13/131 | — |
| M3 | NoCache | race | native | 162/495 | 16.364 | 0/26/136 | — |
| M3 | NoCache | race | fast | 163/497 | 16.398 | 0/25/138 | — |
| M3 | NoCache | race | full | 161/494 | 16.296 | 0/24/137 | — |
| M4 | NoCache | practice | native | 154/491 | 15.682 | 0/24/130 | — |
| M4 | NoCache | practice | fast | 218/493 | 22.110 | 0/192/26 | — |
| M4 | NoCache | practice | full | 214/489 | 21.881 | 0/186/28 | 3.14/2.97; 27.48/35.20; 3.51/10.30; 5.17/5.54; 3.38/3.06; 1.09/1.10; 0.16/0.16; 0.83/0.32 |
| M4 | NoCache | race | native | 166/495 | 16.768 | 0/35/131 | — |
| M4 | NoCache | race | fast | 229/497 | 23.038 | 0/198/31 | — |
| M4 | NoCache | race | full | 234/496 | 23.589 | 0/209/25 | 3.08/4.94; 24.94/34.51; 4.01/8.96; 5.43/5.57; 3.14/3.13; 1.09/1.10; 0.16/0.16; 0.84/9.53 |
| M5 | CACHE | practice | native | 194/496 | 19.556 | 0/118/76 | — |
| M5 | CACHE | practice | fast | 301/498 | 30.221 | 137/147/17 | — |
| M5 | CACHE | practice | full | 313/496 | 31.552 | 166/128/19 | 1.84/1.45; 16.02/20.35; 5.74/14.56; 3.80/4.01; 2.29/2.24; 0.93/1.09; 0.12/0.14; 0.57/0.39 |
| M5 | CACHE | race | native | 212/497 | 21.328 | 0/147/65 | — |
| M5 | CACHE | race | fast | 303/497 | 30.483 | 117/178/8 | — |
| M5 | CACHE | race | full | 373/498 | 37.450 | 252/117/4 | 1.30/3.05; 14.33/19.96; 3.71/14.17; 3.92/4.03; 2.23/2.22; 0.92/1.10; 0.12/0.12; 0.54/0.21 |
| M5 | NoCache | practice | native | 194/496 | 19.556 | 0/118/76 | — |
| M5 | NoCache | practice | fast | 301/498 | 30.221 | 137/147/17 | — |
| M5 | NoCache | practice | full | 313/496 | 31.552 | 166/128/19 | 1.84/1.45; 16.02/20.35; 5.74/14.56; 3.80/4.01; 2.29/2.24; 0.93/1.09; 0.12/0.14; 0.57/0.39 |
| M5 | NoCache | race | native | 212/497 | 21.328 | 0/147/65 | — |
| M5 | NoCache | race | fast | 303/497 | 30.483 | 117/178/8 | — |
| M5 | NoCache | race | full | 373/498 | 37.450 | 252/117/4 | 1.30/3.05; 14.33/19.96; 3.71/14.17; 3.92/4.03; 2.23/2.22; 0.92/1.10; 0.12/0.12; 0.54/0.21 |
| M5 @ 8 MHz | NoCache | practice | full | 201/488 | 20.594 | 0/150/51 | — |
| M6 | CACHE | practice | native | 368/498 | 36.948 | 248/110/10 | — |
| M6 | CACHE | practice | fast | 490/499 | 49.098 | 481/9/0 | — |
| M6 | CACHE | practice | full | 490/499 | 49.098 | 481/9/0 | 0.58/0.88; 8.37/10.86; 5.75/8.69; 3.19/3.26; 1.42/1.50; 0.41/0.41; 0.11/0.12; 0.16/0.15 |
| M6 | CACHE | race | native | 325/497 | 32.696 | 158/162/5 | — |
| M6 | CACHE | race | fast | 494/499 | 49.499 | 489/5/0 | — |
| M6 | CACHE | race | full | 498/499 | 49.900 | 497/1/0 | 0.72/1.91; 7.64/10.80; 6.21/8.59; 3.25/3.26; 1.46/1.55; 0.40/0.41; 0.11/0.12; 0.20/0.15 |
| M6 | NoCache | practice | native | 178/497 | 17.907 | 0/69/109 | — |
| M6 | NoCache | practice | fast | 414/498 | 41.566 | 350/54/10 | — |
| M6 | NoCache | practice | full | 419/499 | 41.984 | 358/51/10 | 0.66/1.13; 13.62/16.87; 2.47/12.49; 3.18/3.26; 1.94/2.09; 1.13/1.24; 0.11/0.12; 0.38/0.15 |
| M6 | NoCache | race | native | 198/496 | 19.960 | 0/108/90 | — |
| M6 | NoCache | race | fast | 373/498 | 37.450 | 250/121/2 | — |
| M6 | NoCache | race | full | 445/498 | 44.679 | 392/53/0 | 1.08/2.73; 11.93/17.34; 2.47/9.86; 3.25/3.26; 2.04/2.16; 1.13/1.24; 0.11/0.11; 0.47/0.15 |
| M6 @ 8 MHz | NoCache | practice | full | 382/498 | 38.353 | 288/84/10 | — |
| M7 | CACHE | practice | native | 404/499 | 40.481 | 319/75/10 | — |
| M7 | CACHE | practice | fast | 490/499 | 49.098 | 481/9/0 | — |
| M7 | CACHE | practice | full | 490/499 | 49.098 | 481/9/0 | 0.56/0.84; 7.92/10.31; 6.31/9.13; 3.19/3.26; 1.37/1.44; 0.39/0.40; 0.11/0.11; 0.15/0.15 |
| M7 | CACHE | race | native | 333/499 | 33.367 | 168/164/1 | — |
| M7 | CACHE | race | fast | 499/499 | 50.000 | 499/0/0 | — |
| M7 | CACHE | race | full | 499/499 | 50.000 | 499/0/0 | 0.66/1.79; 7.23/10.33; 6.75/9.05; 3.25/3.26; 1.42/1.51; 0.39/0.40; 0.11/0.11; 0.23/0.15 |
| M7 | NoCache | practice | native | 178/497 | 17.907 | 0/70/108 | — |
| M7 | NoCache | practice | fast | 429/499 | 42.986 | 378/41/10 | — |
| M7 | NoCache | practice | full | 428/499 | 42.886 | 377/41/10 | 0.60/1.12; 13.31/16.47; 2.35/12.47; 3.18/3.26; 1.93/2.08; 1.12/1.23; 0.11/0.12; 0.38/0.15 |
| M7 | NoCache | race | native | 199/497 | 20.020 | 0/110/89 | — |
| M7 | NoCache | race | fast | 376/497 | 37.827 | 256/119/1 | — |
| M7 | NoCache | race | full | 450/498 | 45.181 | 402/48/0 | 1.03/2.55; 11.69/16.75; 2.59/10.30; 3.25/3.26; 1.99/2.17; 1.13/1.24; 0.11/0.11; 0.50/0.15 |
| M7 @ 8 MHz | NoCache | practice | full | 382/498 | 38.353 | 288/84/10 | — |

All six published native Practice references (M1, M2, M4–M7) reproduce exactly:
zero interval error per 500 fields, against the one-interval tolerance. M3 supplies
a new baseline. The 8 MHz full/NoCache Practice checks are slower: M5 20.594 versus
31.552 fps, M6 38.353 versus 41.984, and M7 38.353 versus 42.886.

M1 full timing measures 99/473 = 10.465 fps versus 104/456 = 11.404 native,
an 8.23% loss; race loses 6.64% (104/485 versus 113/492). D2 therefore retains
native timing on 68000/68010. This phase does not implement the release defaults.
B3's 100-field uninstrumented M1 instruction trace contains 100 complete 20 ms
world steps. Mean cost is **10,357.86 cycles**, p95 **18,778**, range 7,406–23,162.
At 142,102 clocks per nominal 20 ms PAL field, that is 1.458 ms mean and 2.643 ms
p95 (7.29% and 13.21% of the field budget). The measured body starts at
`timing_world_begin` and ends after the committed +4 world-clock update. It includes
interrupts, but excludes frame allocation, rendering/HUD-owned work and the
post-commit loop/restore tail. This body cost alone is not the total scheduler
overhead; the 500-field fps comparison includes all work and decides D2.
Evidence: `tmp/phase-b/b3-m1-world-trace/`, matching `full-verify.lst`, and
`b3-world-cost.json`.

On M6/M7 with NoCache, exclusive rendering takes about 13.62/13.31 ms per
Practice presentation, roughly 58% of the measured frame. Copy costs about
3.18 ms (13.5–13.8%), HUD 1.94/1.93 ms (8.2–8.4%), and handshake wait
2.47/2.35 ms (10.5/10.2%). With CACHE, rendering drops to 8.37/7.92 ms;
copy stays at 3.19 ms and HUD costs 1.42/1.37 ms. These identify copy and HUD
as candidates above Phase C's 3% threshold, not proven achievable savings.
Presentation including LoadView is only about 0.11 ms, below 1%, so the B2
measurements do not justify a narrower LoadView replacement.

CACHE full timing reaches 49.098 fps in Practice on both M6 and M7, and
49.900/50.000 in race. At that rate the roughly 5.75/6.31 ms Practice wait
also paces the display; removing its full cost cannot lift PAL presentation
above 50 fps. M5's CACHE and NoCache baseline counts match on both routes.
These are results of the requested emulator/WHDLoad configurations, not a
new cache policy or physical-board certification. Phase C findings follow below.

The final B1 M4 trace covers 46 common complete intervals; all exclusive phase sums
agree with instruction-cost attribution within 0.00571%. The actual render-return
hook includes incident paths that skip the HUD. The corrected 500-field M4 phase
capture also completes successfully. Long-tail incidents can put a phase's mean
above its p95; these are measured values, not a stationary scene benchmark.

## Phase C measurements and decisions

Phase C is complete. C1 and C2 are retained; C3 needs no change; C4 is rejected.
Phase D is also complete. Release defaults and WHDLoad cache policy are unchanged.
The Phase B table above remains the frozen comparison baseline.

Final full-timing Practice throughput, NoCache, 500-field driving windows:

| Machine | Phase B fps | Retained Phase C fps | Change |
| --- | ---: | ---: | ---: |
| M4 | 21.881 | 24.291 | +11.01% |
| M5 | 31.552 | 39.178 | +24.17% |
| M6 | 41.984 | 45.291 | +7.88% |
| M7 | 42.886 | 45.792 | +6.78% |

With CACHE, M5 also reaches 39.178 fps; M6/M7 remain at 49.098 fps. These gains
are end-to-end route throughput, not fixed-scene instruction-cost comparisons.
The retained defaults are unchanged; this is not a claim that every machine now
reaches 50 fps.


### Wait-overlap candidate performance (C1)

Uninstrumented full timing, Practice, 500 fields at `$bc7c`, `SWAP_ONLY=1`.
The candidate passes: all NoCache accelerator gains exceed 3%, CACHE improves on M5
and holds the near-50-fps M6/M7 baseline.

| Machine | WHDLoad | Before intervals/fields | C1 intervals/fields | fps | Change |
| --- | --- | ---: | ---: | ---: | ---: |
| M4 | NoCache | 214/489 | 238/495 | 21.881 → 24.040 | +9.87% |
| M5 | CACHE | 313/496 | 382/499 | 31.552 → 38.277 | +21.31% |
| M5 | NoCache | 313/496 | 382/499 | 31.552 → 38.277 | +21.31% |
| M6 | CACHE | 490/499 | 490/499 | 49.098 → 49.098 | +0.00% |
| M6 | NoCache | 419/499 | 443/499 | 41.984 → 44.389 | +5.73% |
| M7 | CACHE | 490/499 | 490/499 | 49.098 → 49.098 | +0.00% |
| M7 | NoCache | 428/499 | 448/499 | 42.886 → 44.890 | +4.67% |

The C1 beam-ordering gate passes on all four machines (100 fields each), with
308 checked staged copies. Each wait completes in a VBL later than the preceding
presentation; each copy sample follows the completed wait sample. Costs below are
beam-clock units, not CPU-frequency-scaled cycles. The 100-field M4/M5/M7 twin
runs complete 16/26/29 staged scenes, with zero pixel, register/CCR, scratch or guard
failures and unchanged copied raster code. C1 is retained.

| Machine | Copies checked | Minimum fields after present | Minimum beam clocks after wait |
| --- | ---: | ---: | ---: |
| M4 | 48 | 1 | 156 |
| M5 | 78 | 1 | 92 |
| M6 | 90 | 1 | 46 |
| M7 | 92 | 1 | 46 |

### Buffer ownership before moving the wait (C1)

`audit_buffer_writes.py` lists every observed CPU bitmap writer and extent in
`tmp/phase-c/c1-buffer-audit.json` and `c1-weather-buffer-audit.json`.
The normal M4 full-timing trace covers 47 scene entries in 100 fields. The directed
weather trace covers 31 scene entries and eight effect draws in 100 fields.
Neither audit has an unhandled memory operation. The accompanying code-write audits
find no game-code writes in the staged trace, but weather fallback rewrites each
native span branch displacement 203 times.

| Work | Observed chip writes | Consequence |
| --- | --- | --- |
| Staged scene | Final MOVEM transfer only, rows 19–153 in each plane | Wait may move immediately before this copy. |
| Native weather fallback | Clear at `$1582c`, span writers in `$15b68`–`$15e68`, plus KickEmu blitter setup during the weather draw path | Keep the original wait at `$112a6` whenever staging is inactive. |
| HUD and post-render work | Writers in `$15612`–`$175c6`, rows 156–199, plus blitter setup | Remain after the completed copy/handshake. |
| Timer | Writers at `$16d4e`/`$16d60` and `$173e4`–`$173f0`, rows 4–12 | Remain on chip RAM after the handshake. |

The weather path through `$112f4` is excluded by the existing effect/lifetime
staging checks. Twin reference blocks write chip RAM inside the renderer; their
VERIFY path retains the early wait. Production staged drawing defers it to copy.
The CPU audit separately reports blitter-register writes; it does not claim CPU
trace coverage of DMA or unexecuted routes.

### Static raster routing (C2, retained)

The candidate uses static raster code for every polygon on 68020+ when that code
is installed, including scenes that retain native chip bitmap and edge pointers.
68000/68010 retain their previous staged-only routing. Bitmap-only diagnostic
modes do not claim that static code is installed.

The M4 200-field Practice trace from `$14764` contains 16 subsequent pit-motion
entries, 28 renderer entries and 17 driving presentations. The code-write audit
reports zero writes to executed game instructions and no unhandled operations;
the reference rewrites each native branch displacement 313 times. The initial
pit and title screenshots are pixel-identical. Evidence is under `tmp/phase-c/c2/`.
M4/M5/M7 twins complete 16/26/29 staged scenes in 100 fields each, with zero
pixel, register/CCR, scratch or guard failures and unchanged copied raster code.
All NoCache throughput comparisons improve; CACHE improves on M5 and holds the
M6/M7 baseline. These small gains are not claimed as a 3% performance optimization:
C2 is retained under its specific no-self-modifying-code correctness gate.

| Machine | WHDLoad | C1 intervals/fields | C2 intervals/fields | fps | Change |
| --- | --- | ---: | ---: | ---: | ---: |
| M4 | NoCache | 238/495 | 240/494 | 24.040 → 24.291 | +1.04% |
| M5 | CACHE | 382/499 | 391/499 | 38.277 → 39.178 | +2.36% |
| M5 | NoCache | 382/499 | 391/499 | 38.277 → 39.178 | +2.36% |
| M6 | CACHE | 490/499 | 490/499 | 49.098 → 49.098 | +0.00% |
| M6 | NoCache | 443/499 | 452/499 | 44.389 → 45.291 | +2.03% |
| M7 | CACHE | 490/499 | 490/499 | 49.098 → 49.098 | +0.00% |
| M7 | NoCache | 448/499 | 457/499 | 44.890 → 45.792 | +2.01% |

### Copy, HUD and presentation assessment (C3)

No C3 code change is justified by the prescribed candidates. Copy already uses
ten-register, 40-byte MOVEM blocks for the 21,600-byte extent. Both bitmap bases in all seven M4–M7 C1 performance captures, the 760-byte copy
offset and the 8,000-byte plane stride are longword-aligned (`c3-alignment.json`).
HUD writes extend outside rows 19–153, failing the plan's prerequisite for staging
HUD in that extent; it also uses the blitter. Leave it native. B2 measures the whole
presentation call, including LoadView, at about 0.11 ms on M6/M7, below 1% of a frame
and therefore below the 3% investigation threshold. No MOVE16 or cache-policy change
is introduced.

### Stock A1200 chip-code trial (C4, rejected)

M3 with WHDLoad CACHE, full timing, Practice, 500 fields from `$bc7c`:

| Configuration | Intervals/fields | fps | Fields 1/2/3+ |
| --- | ---: | ---: | --- |
| Native raster control | 144/494 | 14.575 | 0/13/131 |
| Static raster code in chip RAM, no staging | 139/495 | 14.040 | 0/8/131 |

The candidate is 3.67% slower, failing the required 3% gain. Its live snapshot confirms
that static code is in chip RAM, the bitmap pointer is zero, and copied code remains
unchanged. Only the code portion of the existing chip-backed private arena was used;
there was no production staging bitmap. The experiment and its assembly flag are
removed. M3 keeps native raster routing. No twin acceptance is claimed or needed for
a candidate rejected by its performance gate. Evidence: `tmp/phase-c/c4/decision.json`
and the two matched captures.

The chip-only capture helper now selects chip memory for its slave snapshot and
rejects missing/short dumps. Older M3 auxiliary dumps could retain unrelated scratch
contents after an unmapped slow-memory read; they are not used for C4 diagnostics.
The earlier M3 driving counts used live chip-resident game/VBL addresses and the
new control reproduces the full-timing 144/494 count.

## Phase D: A500 measurements and decisions

Phase D is complete. **A500 unchanged at 11.404 fps.** No renderer, timing, option
or cache-policy change is retained. Phase E has not started.

### Pipelined blitter clear (D1, rejected)

The trial fills the four separate planar extents (rows 19–149, 5,240 bytes each)
with D-only constant-color blits. It starts plane 0 at renderer entry, then planes
1–3 after camera transformation, near clipping and projection. It owns the blitter,
waits before reprogramming it, and drains the last plane before polygon drawing.
Only the normal cockpit clear is eligible; the special-color early return stays
native. Because this draws directly into the old front buffer, the display
handshake must happen **before** the first blit, rather than after geometry.

Both measurements use M1: PAL 68000, 512 KiB chip, 1.5 MiB slow, no fast RAM,
WHDLoad NoCache, native timing and fixed Practice input (`CUSTOM5=2`). The trial
was selected through `CUSTOM1=1`; the normal control has it off. Playback uses
`SWAP_ONLY=1`, 500 fields from `$bc7c`; traces are separate 100-field captures
from the same anchor. No trace-derived fps is used.

| Configuration | Driving intervals/fields | fps | Complete traced frames | Mean cycles/frame | p95 cycles/frame |
| --- | ---: | ---: | ---: | ---: | ---: |
| Native control | 104/456 | 11.404 | 21 | 641,039.43 | 754,546 |
| Pipelined blitter clear | 104/494 | 10.526 | 20 | 665,936.60 | 808,556 |

Playback is **7.69% slower**, and mean completed-frame cost is **3.88% higher**,
failing the required 3% improvement and non-regressing fps gate. Both windows
have fixed input, but native frame-dependent simulation changes later scenes;
these are route/frame costs, not an identical-polygon instruction comparison.

The trace confirms 80 plane blits in the 20 complete trial intervals, with no
native clear calls in the full trial trace. The work was replaced, not bypassed
by a dormant option. Exclusive CPU instruction costs per complete frame explain
why removing the clear does not help:

| Work | Native cycles/frame | Trial cycles/frame |
| --- | ---: | ---: |
| CPU background clear | 52,964.19 | 0 |
| Original display wait | 4,823.24 | 21.80 |
| Earlier display wait | 0 | 57,788.10 |
| Trial blitter polling | 0 | 8,767.30 |
| Other trial wrapper/setup instructions | 0 | 2,975.30 |
| Geometry instructions | 83,333.33 | 93,041.40 |

The extra early handshake nearly consumes the whole removed CPU-clear cost.
Blitter polling and setup add more work. Geometry also costs more in this route;
the trace does not separate contention from changed scene inputs. Frame totals
include interrupts; these instruction buckets are exclusive and do not include
interrupt time inside the waits.

The candidate was dropped after this one performance evaluation. No twin gate
was run or passed for the rejected implementation. Its source and frozen slave
remain only in ignored scratch evidence; the trial hooks and assembly flag are
removed from the repository. The normal build is byte-identical to the Phase D
control: SHA-256 `ca8639921c1d8c2781578a62a42003a6ba888990a4a22b8d4f82cc829be061f3`.

### Individual Kickstart calls (D2, below threshold)

The original A500 trace's complete track fields 191–499 contain 43,909,542 CPU
cycles. The existing call-stack report splits the approximately 9.6% Kickstart
share as follows. Figures are inclusive call costs; nested rows must not be summed.
VBL server identities were checked against the snapshot's Exec VERTB list.

| Call | Calls | Cycles | Mean cycles/call | Share of track window |
| --- | ---: | ---: | ---: | ---: |
| BltBitMap | 138 | 1,132,852 | 8,209.07 | 2.580% |
| MakeVPort | 32 | 588,782 | 18,399.44 | 1.341% |
| gameport.device VBL server | 309 | 517,616 | 1,675.13 | 1.179% |
| LoadRGB4 | 16 | 460,792 | 28,799.50 | 1.049% |
| MrgCop | 32 | 431,802 | 13,493.81 | 0.983% |
| WaitBOVP | 16 | 240,596 | 15,037.25 | 0.548% |
| Game VBL callback at `$5684` | 309 | 222,914 | 721.40 | 0.508% |
| Unnamed VBL server | 309 | 134,716 | 435.97 | 0.307% |
| VBeamPos | 1,425 | 126,292 | 88.63 | 0.288% |
| LoadView | 85 | 81,598 | 959.98 | 0.186% |

Interrupt-stack execution totals 1,604,382 cycles (3.654%), but contains several
servers, game work and dispatch overhead; it is not one replaceable call.
No individual identified OS call or VBL callback meets 3%, so D2 retains the OS
paths. In particular, narrowing LoadView cannot recover the aggregate 9.6%.

### Static chip-RAM span dispatch (D3, below prerequisite)

The existing static implementation preserves the native span writers and the
68000 row arithmetic. The difference is color dispatch and its return path.
In the original trace, all mutable dispatch setup at `$1600c–$16020` costs
79,494 of 43,948,270 track cycles: **0.181%**. The two branch writes at `$16012`
and `$1601c` account for 48,684 cycles across 2,558 writes (0.111%). Even deleting
the entire setup for free cannot meet the 3% frame threshold, and static dispatch
still needs replacement setup and indirect span returns. This is an upper bound,
not a measured static-raster speedup.

There is no qualifying M1 twin result, so the plan's conditional chip-code trial
is not pursued. The earlier 68000 address-loop refinement also failed its playback
gate, but that fast-RAM result is not treated as a measurement of this M1 path.
No static chip-code or further arithmetic experiment is retained.

### Evidence and reproduction

Evidence is under `tmp/phase-d/`: `baseline-fps`, `d1-fps`, `baseline-trace`,
`d1-trace`, their frame/fill cost JSON, `d2-calls.json`, `kick-calls.txt`, and
`d3-upper-bound.json`. Captures retain effective configuration and binary hashes.
The D2/D3 input is `tmp/prof/practice-continuous-10s/trace.bin`.

For the current unchanged M1 rate, freeze a fresh VERIFY build and run:

```sh
source amiga/env.sh
make -C whdload verify
SWAP_ONLY=1 FIELDS=500 ANCHOR=0xbc7c WHD_ARGS='CUSTOM5=2 NoCache' \
  tools/fixed_window.sh tmp/phase-d-repeat tmp/build/Powerdrome-verify.slave
make -C whdload all
```

The per-call attribution uses `tools/powerdrome_report.py` with the existing
capture's slave, memory dump and `--fields 191-499 --top 90`. Frame-cycle evidence
sums every instruction between successive `$bc7c` hits, excluding incomplete
edge intervals. No further A500 optimization is queued by this phase.

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
  The title route repeats without a seed override; racing remains unverified.

The Practice trace now confirms the normal loop's order: `$ca3e` updates movement, calls the
scene renderer at `$cee8`, runs post-render gameplay/HUD work, then the caller presents through
`$bc7c`/`$8056`. There are 70 player movement updates and 70 renderer entries; the 69 completed
iterations each reach the native delta calculation. All 68 adjacent sampled presentations have
raw delta equal to four times their PAL-field separation. Observed deltas are 12–32, without
clamping. Simulation is coupled to rendering but its main displacement uses elapsed time.
See the [performance plan](performance-plan.md) for the per-loop behavior and fast planar
buffer design. The selected scope preserves the native simulation and timing policy.

## Development slave and reproducible title-demo profile

`whdload/Powerdrome.s` uses unmodified WHDLoad 20 KickEmu sources, interface 17, one disk,
512 KiB chip for the guest, 256 KiB expansion for Kickstart and 128 KiB additional guest
expansion. It retains the EndCLI redirection and Copylock replacement, with a signature
check at game `$843c`. Cache selection is left to standard WHDLoad options. `CUSTOM1=1` enables the optional fast planar
renderer, described in the [implementation report](performance-implementation.md); it is
off by default. In VERIFY builds only, CUSTOM5 replaces the name-entry key-ready
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
