# Powerdrome practice departure profile

Project status: Phases A–E are complete within the agreed scope, with steady A500 handling and natural-weather validation deferred by the user. Neither deferred gate is counted as passed. Phase F is stopped at the stock-A1200 throughput gate; release validation is incomplete.
See the [current handoff](open-work.md) for completed checks, open gates and resume priorities.

CPU polygon drawing is the principal bottleneck during the track portion of this A500 run.
Edge construction and span filling take **54.27% of recorded track cycles**. Background filling
adds **8.45%**, viewport clipping **5.25%**, and camera transformation, near-plane clipping,
projection and visibility checks another **10.98%**. These are disjoint instruction costs.
The measured drawing blocks, including renderer dispatch, account for **80.59%** before
adding the renderer's VBL wait or drawing work elsewhere in the game and operating system.

The pit has a different bottleneck: **47.05%** of its cycles execute KickEmu's WaitBlit.
That falls to **0.17%** on track. Optimizing the launch wait would have little effect on the
track portion. The first targets for investigation are the per-scanline polygon loop, its
four-plane span writers and edge stepping; background clearing is a smaller, regular target.
No optimization or speedup is claimed here. The [implementation plan](performance-plan.md)
examines planar staging in fast RAM, measured bitmap traffic and simulation integration.

## Capture and scope

This is the continuous capture at `tmp/prof/practice-continuous-10s/`, produced with the
VERIFY development slave at revision `0efcd3d`, `CUSTOM5=2`, and movement anchor `$14764`.
The fixture follows Enter → Practice → Space. The capture begins at the first pit-departure
animation iteration, after the stationary pit delay. It includes the ship leaving the pit,
screen transition, cockpit departure and subsequent track gameplay.

Configuration: PAL, 68000, 512 KB chip RAM, 1,536 KB slow RAM, no fast RAM, WHDLoad 20 and
KickEmu with guest Kickstart 1.3. The game has no performance patches. Results describe
emulated A500 execution, not host CPU usage or measurements from physical hardware.

The trace contains **500 consecutive fields**, ten nominal PAL seconds, **71,050,998
recorded CPU cycles**, **6,205,664 instruction records**, and **500 game VBL callbacks**.
Every instruction record has a PC. The first 100 fields match the earlier short capture's
initial chip memory and CPU/DMA records exactly. A second complete 500-field fresh-boot
comparison is still pending. The older capture assembled from short chunks has gaps and
is not used for these measurements.

## Four distinct phases

Phase boundaries are the first executions of the markers below. CPU costs switch phase
at that instruction, so a boundary field is split exactly in the CPU accounting. Times are
rounded nominal PAL times; field numbers are zero based.

| Phase | Boundary | Approximate time from start | Recorded cycles | Share of run |
| --- | --- | ---: | ---: | ---: |
| Pit animation | Capture anchor `$14764` | 0–1.12 s | 7,992,080 | 11.25% |
| Transition | Pit animation return `$147a6`, field 56 | 1.12–2.44 s | 9,434,916 | 13.28% |
| Cockpit departure | Entry `$1020e`, field 122 | 2.44–3.80 s | 9,675,732 | 13.62% |
| Track | First main-loop entry `$ca3e`, field 190 | 3.80–10.00 s | 43,948,270 | 61.85% |

The pit spends 3,760,542 cycles in WaitBlit and 3,126,686 in other Kickstart code, respectively
47.05% and 39.12% of that phase. STOP records add 3.66%. This is the phase where blitter
completion and system graphics activity dominate.

During transition, the bitmap unpack loop at `$79b4–$7a0e` takes 2,401,242 cycles, **25.45%**
of the phase. All its measured cost occurs here. Its literal/repeated-byte paths implement
bitmap decompression; the repeated-byte loop at `$7a00` is particularly busy. Other Kickstart
code takes 56.54%, and code outside the identified game/slave/Kickstart regions takes 9.08%.
Those remaining costs are not assigned to disk latency: the profile does not establish that
interpretation, particularly with WHDLoad preloading. This phase is a separate loading and
screen-setup target.

Cockpit departure contains ten renderer entries and ten returns. Polygon edge/span work
already takes 42.19%, background filling 5.45%, and other Kickstart code 27.77%. The native
`$1020e` path and its `$10338` helper perform the departure views before the regular main
loop starts. Costs from this sequence should not be pooled into a steady racing baseline.

## Where track cycles go

The track denominator is 43,948,270 recorded cycles. The last column uses the entire
71,050,998-cycle capture, showing how launch work dilutes recurring gameplay costs.
Rows are mutually exclusive and sum to 100% of track cycles apart from rounding.

| Executed work | Track cycles | Track share | Whole-run share |
| --- | ---: | ---: | ---: |
| Polygon span setup and iteration | 9,771,092 | 22.23% | 16.08% |
| Multiword span writes | 7,430,778 | 16.91% | 12.02% |
| Polygon edge setup and stepping | 6,343,086 | 14.43% | 10.63% |
| Kickstart other | 4,198,484 | 9.55% | 21.60% |
| CPU background fill | 3,712,482 | 8.45% | 5.97% |
| Game other | 3,213,174 | 7.31% | 7.04% |
| Polygon clipping | 2,309,064 | 5.25% | 3.75% |
| Camera transform and setup | 2,045,454 | 4.65% | 3.59% |
| Perspective projection and setup | 1,580,338 | 3.60% | 2.77% |
| VBL handshake wait | 832,390 | 1.89% | 1.17% |
| Visibility and backface checks | 827,692 | 1.88% | 1.49% |
| Renderer dispatch and other inline work | 723,644 | 1.65% | 1.26% |
| Near-plane clipping | 371,188 | 0.84% | 0.63% |
| Singleword span writes | 305,194 | 0.69% | 0.58% |
| Slave other | 100,684 | 0.23% | 0.36% |
| KickEmu WaitBlit | 75,224 | 0.17% | 5.60% |
| Unmapped | 68,108 | 0.15% | 1.54% |
| Interrupt entry | 40,194 | 0.09% | 0.13% |
| Bitmap unpack | 0 | 0.00% | 3.38% |
| STOP records | 0 | 0.00% | 0.41% |

“Other” means outside the explicitly classified ranges, not idle time. Game other includes
control, simulation, display updates, additional drawing and interrupt work. Kickstart other
includes library/system execution and interrupt handling. No individual unidentified track
instruction exceeds 0.2% of the track total; the residual cost is distributed. The 0.09%
interrupt-entry row is just the entry records, not the full cost of interrupt handlers.

Phase D attributes the Kickstart share per call: BltBitMap is 2.580%, LoadView
0.186%, and no individual traced VBL callback reaches 3%. Its pipelined blitter
clear is rejected after lower fps and higher frame-cycle cost. The A500 remains
at 104/456 = 11.404 fps; see [Phase D measurements](internals.md#phase-d-a500-measurements-and-decisions).

## Why polygon drawing is expensive

The renderer draws directly into four planar bitmaps. It computes polygon edges into a
scratch table, then walks the covered scanlines. Each scanline needs left/right positions,
word addresses, masks, a choice of writer, and writes to the appropriate bits in all four
planes. Many instructions repeat for every row of every polygon.

| Block | Game-hunk range, end exclusive | Track share | Mechanism |
| --- | --- | ---: | --- |
| Edge setup and stepping | `$15ee8–$15fd4` | 14.43% | Compute fixed-point slopes and write edge X coordinates for each row |
| Span setup and iteration | `$15fd4–$1609c` | 22.23% | Read edges, order endpoints, form masks and word addresses, dispatch and advance rows |
| Multiword span writers | `$15b68–$15da8` | 16.91% | Mask first/last words and write interior words across four planes |
| Singleword span writers | `$15da8–$15e68` | 0.69% | Apply combined masks when both endpoints occupy one word |

Together these consume **23,850,150 track cycles**. The trace reaches the rasterizer entry
1,281 times and the scanline loop `$1602a` 38,362 times in the track phase. These are executed
entry/loop counts, not a count of unique visible polygons or pixels; the last renderer is
partially captured and polygons can overlap.

The edge loops at `$15f3e` and `$15f9e` repeatedly shift an 8.8 fixed-point coordinate right
by eight and store its integer part. Just the two `ASR.L #8` instructions at `$15f40` and
`$15fa0` cost **1,512,770 cycles, 3.44% of track time**. Repeated shifts, edge-table traffic
and loop control merit investigation together; accelerating only the slope division would
leave most edge work intact. Vertical edges already have a simpler constant-X path.

Span setup is the largest single classified block. It constructs left/right masks and
converts X coordinates to planar word offsets on every row. Multiword writers then perform
four-plane boundary updates and interior stores. The implementation already specializes
writers by color and patches dispatch branches at `$16080` and `$1608a`. Any replacement
must preserve those entry paths and color-dependent masking. CPU code, data and bitmap
accesses also contend for the chip bus, so instruction counts alone cannot predict savings.

## Background filling and geometry

Background filling (`$1578a–$15836`) costs **3,712,482 track cycles**. The inner store at
`$1582c` is the single hottest track instruction: **3,251,890 cycles, 7.40%**. Each
`MOVEM.L` stores ten registers, or 40 bytes. There are 36,680 such stores during track
execution, **1,467,200 bytes of background writes**, before polygon writes. The 280 plane
fill entries comprise 140 zero fills and 140 one fills; both entries share the store loop.
This is a regular four-plane workload rather than a complex drawing decision.

The camera transform/setup (`$10df2–$10f1e`) takes 4.65%, near-plane clipping
(`$10f1e–$10fc6`) 0.84%, perspective projection/setup (`$10fc6–$1108e`) 3.60%, and
visibility/backface checks (`$1108e–$1118c`) 1.88%. The two principal perspective `DIVS`
instructions at `$1100a` and `$1104c` total **735,564 cycles, 1.67% of track time**.
The transform contains repeated signed multiplies, while projection uses signed division
and overflow fallback paths. Faster arithmetic is a secondary candidate relative to
per-scanline rasterization; these two divisions alone cannot deliver a large total saving.

Viewport polygon clipping (`$1609c–$163e2`) adds **5.25%**. It clips against boundaries and
calculates intersections, then can branch directly to `$15ee8`. Its geometry and overflow
semantics need preserving independently of the downstream rasterizer. More aggressive
culling or avoiding repeated edge work could change how much reaches this stage, but the
capture alone does not establish how much work can safely be removed.

## Waits, DMA and observed cadence

The renderer's VBL handshake at `$112a6/$112aa` costs **832,390 track cycles, 1.89%**.
Complete KickEmu WaitBlit costs **75,224 cycles, 0.17%**. There are no track STOP records.
These small measured wait shares support CPU drawing as the primary track target. They
do not prove that faster drawing will scale linearly: synchronization and bus contention
can become more important after other work is reduced.

DMA slot occupancy independently supports the difference between pit and track. Boundary
fields are excluded here because DMA records are classified by whole field. CPU-cycle
shares and DMA-slot shares measure different things and must not be added together.

| Phase | Complete fields used | CPU slots | Blitter slots | Bitplane slots | Free slots |
| --- | --- | ---: | ---: | ---: | ---: |
| Pit | 0–55 | 26.05% | 31.86% | 22.52% | 17.45% |
| Transition | 57–121 | 42.20% | 0.33% | 22.52% | 32.83% |
| Cockpit departure | 123–189 | 38.80% | 0.20% | 22.52% | 36.34% |
| Track | 191–499 | 38.49% | 0.24% | 22.52% | 36.54% |

The omitted DMA slots are refresh, copper and audio. Track blitter occupancy is only
0.24%, versus 31.86% during the pit. The 36.54% free-slot figure does not mean the CPU is
36.54% idle: internal CPU operations and the timing of available slots matter. It suggests
that a blitter-assisted background-fill experiment is worth measuring, not that it is
already known to outperform the CPU loop.

There are 70 track main-loop entries, 70 renderer entries, 69 renderer returns and 69
`$8056` display-update entries. The final renderer is cut off by the capture boundary.
Across the 69 complete entry-to-return windows, elapsed recorded cycles average 538,293
(median 549,440; range 360,808–719,458). These include interrupts and waits within each
window; they are not isolated main-task execution costs. They correspond to about
75.8 nominal milliseconds on this trace's cycle scale.

The 68 intervals between renderer returns span 302 PAL fields, about 11.26 returns per
nominal second. Intervals are 3 fields (18 occurrences), 4 (21), 5 (19), 6 (2), 7 (7),
and 8 (1). This is **renderer-return cadence**, not validated displayed FPS. `$8056` also
runs in departure paths, and frame completion still needs comparison with display changes
and an independent counter. The route changes view during these six seconds, so neither
this cadence nor a mean call cost represents every racing scene.

## Optimization priorities and constraints

1. **Polygon scanlines and span writers, 39.84% together.** First investigate repeated
   endpoint/mask/address setup and the four-plane write loops. Measure narrow and wide
   spans separately before choosing specialization or a different representation. Preserve
   edge masks, color writers, self-modified dispatch and all entry points.
2. **Edge stepping, 14.43%.** Investigate fixed-point extraction, scratch-table access and
   loop overhead. A replacement must preserve signed coordinates, rounding, clipping and
   overflow handling. The two hot shifts provide a concrete 3.44% bound for that narrow target.
3. **Background filling, 8.45%.** Compare the existing CPU fill with a blitter-assisted
   implementation or a justified reduction in cleared area. Include setup, synchronization,
   contention and restoration costs; unchanged pixels outside the viewport matter.
4. **Viewport clipping and geometry, 16.23% combined.** Profile individual arithmetic and
   rejection paths before designing replacements. Avoid reciprocal or precision shortcuts
   until equivalence across negative inputs and overflow cases is demonstrated.
5. **Pit and transition separately.** WaitBlit dominates the pit; bitmap unpacking takes
   a quarter of transition time. These are launch-experience candidates, not the leading
   targets for sustained track rendering.

For scale only, halving the entire measured 54.27% polygon edge/span cost, with all other
work and the scene held fixed, would reduce total track cycles by 27.13% and give a
mathematical throughput ratio of about 1.37. Eliminating background filling entirely would
cap its standalone ratio at about 1.09. These are arithmetic bounds, not predicted speedups.
This game's racing motion uses a clock-derived, clamped frame delta, so rendering changes
can also alter the scene reached at a given anchor or field.

Before selecting an implementation, repeat the complete route across fresh boots, validate
racing frame completion, capture the same route on a 68020, and finish the timing/state
coupling checks listed in [open work](open-work.md). Replacement loops need register/flag
and pixel equivalence checks as well as a matched A/B capture. The
[loader audit](loader-equivalence.md) resolves Copylock D2 and records the remaining
allocation/timing differences; this profile does not compare the two loaders.

## Attribution method and reproduction

The analysis uses executed PCs and sums each record's cycle cost into exactly one block.
All code addresses above are game-hunk offsets. WaitBlit is the complete resident slave
range `$034a–$037e`, including its CIA delay reads. STOP opcodes are identified from the
captured memory. The phase-specific instruction, event and DMA totals are saved in the
ignored `analysis.json`; no game, ROM, trace or screenshot bytes belong in git.

The older generic `profile.txt` infers routine boundaries from call targets. That is useful
for exploration but misleading for branch-entered assembly blocks:

- Its `$159e8` label absorbs the color-specialized span writers, despite that entry being
  a different vertical-line routine. The span writers account for the reported hotspot.
- Its `$15810` label misses the distinction between zero-fill entry `$1580c` and one-fill
  entry `$15810`. Both execute the shared background loop.
- The clipper can tail-branch into `$15ee8`, so reconstructed inclusive call costs can be
  smaller than self costs. Such inclusive figures are not used to rank bottlenecks here.

The disjoint ranges in `tools/analyze_practice.py` were checked against the game disassembly.
They include inline setup and loop control, with the VBL polling pair separated from the
surrounding renderer range. They do not attempt a complete symbolic naming of Kickstart,
WHDLoad or every game routine. Unmapped code is retained explicitly: 1.54% of the whole
capture, but only 0.15% of the track phase.

Reproduce the capture with the existing setup from [development](development.md):

```sh
make -C whdload verify
WHD_ARGS=CUSTOM5=2 ANCHOR=0x14764 FIELDS=500 \
  tools/fixed_window.sh tmp/prof/practice-continuous-10s
python3 tools/analyze_practice.py tmp/prof/practice-continuous-10s \
  > tmp/prof/practice-continuous-10s/analysis.json
```

The analyzer reads the capture's own `slave.slave`, `code.bin`, `dump-base.txt` and trace,
locates the loaded regions, and partitions the full instruction stream. It can be rerun
without launching the emulator. The host profiler cap adjustment used to obtain all 500
fields changes only the running profiler command, not the guest game or emulator executable.
