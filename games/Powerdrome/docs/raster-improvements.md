# Raster improvement plan and results

Current release status and validation limits are in [open work](open-work.md).

Scope: further optimize the existing planar fast-memory rasterizer selected on 68020+ with real fast RAM.
Keep the native fallback, CPU compatibility, WHDLoad cache selection and simulation timing.
No chunky rewrite or scheduler changes. The pre-change source reference is `ee3e90f`.

## Progress

| Step | Shortcut | Work and acceptance gate | Status |
| --- | --- | --- | --- |
| 1 | R1 baseline | Freeze current builds; profile identical-input polygon twins on 68020, split edge/span costs, count 500 driving fields independently. | Complete |
| 2 | R2 spans | Simplify plane-address construction and endpoint arithmetic. Verify exact outputs; measure against R1 before selecting. | Complete: address-only candidate selected |
| 3 | R3 edges | Investigate fixed-point extraction and stepping. Preserve signed rounding, overflow fallback, output registers and flags; reject unsafe or unhelpful changes. | Complete: retain native edge arithmetic |
| 4 | R4 validate | Run ten-second drawing twins and independent playback measurements; cover 68000 compatibility and accelerator configurations. | Complete |
| 5 | R5 select | Retain only justified changes, report costs/FPS/memory tradeoffs and rejected candidates, update open work. | Complete |

## Measurement rules

Use frozen slave inputs and the same loader, machine, memory and WHDLoad settings for each
comparison. Use the VERIFY drawing twin for identical-input correctness and polygon costs;
never use its playback rate as a game-performance result. Measure non-twin presentation
intervals over 500 PAL fields from the first driving presentation, and repeat selected
results where noise or a small gain needs checking. Cycle costs are emulator-specific.
Keep absolute counts, not just rounded percentages. Faster playback changes later scene
inputs, so scene-average costs alone do not establish an identical-work speedup.

Every retained candidate must have zero pixel, register/CCR, scratch and guard failures,
unchanged copied code during playback, and intact option-off/fallback hooks. Arithmetic
changes also need boundary tests beyond the one observed route. Unsupported routes remain
native; the completed [gameplay campaign](gameplay-coverage.md) documents longer coverage.

## Starting evidence

The existing implementation's older 68020 driving measurement is 218 intervals / 492 PAL
fields = 22.154 fps, versus 154 / 491 = 15.682 fps native. This is context, not a new result.
The original chip-rendered A500 profile attributes 39.84% of track cycles to span setup and
writers and 14.43% to edges. R1 measures the remaining fast-path bottlenecks directly; the original chip-path shares
are not reused as predictions for further improvements.

## R1: measured baseline

The fresh 68020 baseline has 424 identical-input polygon pairs and no verification failures.
Native/fast paired totals are 9,884,936 / 4,112,150 recorded cycles (interrupts included),
a 58.40% reduction from native. Independent playback completes 218 intervals in 492 PAL
fields: 22.154 fps. This reproduces the preceding implementation's result.

Instruction attribution excludes interrupts and wrapper work:

| Fast-raster work | Cycles | Share |
| --- | ---: | ---: |
| Scanline setup and return | 1,735,580 | 42.90% |
| Span writers | 1,293,995 | 31.99% |
| Edge stepping | 683,399 | 16.89% |
| Edge setup | 264,244 | 6.53% |
| Polygon span setup | 68,045 | 1.68% |
| Total | 4,045,263 | 100% |

Reproduce with `tools/raster_costs.py CAPTURE`; `tools/raster_pairs.py CAPTURE` measures
native/fast twins. `tools/compare_raster_costs.py BEFORE AFTER` matches edge-coordinate
sequences and colour, then sums each shared shape's median fast instruction cost. It excludes
interrupts and gives equal weight to each shared shape, not each occurrence. These figures
cannot replace independent gameplay throughput measurements.

## R2: span candidates

On 68020 and later, plane addressing replaces three MOVEA/LEA pairs with three direct LEAs. All address
values and flags are identical, including 32-bit wraparound. Compacting the loop requires adjusting
the empty-row branch, DBF and static writer branches. Clone stride and native return offset
remain unchanged; three NOPs execute once at polygon return. The copied span writers remain
unchanged. The fast arena size is unchanged.

The first 100-field twin passes all checks. Across 358 shared polygon shapes (394 baseline
and 396 candidate occurrences), summed median instruction costs fall from 3,570,608 to
3,534,544, a 1.010% reduction. Independent playback changes from 218/492 to 218/491 fields,
22.154 to 22.200 fps: only one field, not evidence of a substantial gameplay speedup.

The rejected second candidate replaces word-mask/sign-extension endpoint setup with a long mask.
After the right endpoint shifts, `(d1 & 254)` is in 0..254 for every 32-bit input, so sign
extension is redundant. The following ADD overwrites arithmetic flags, including X. It
saves one instruction per nonempty row. Across 385 shared shapes (423 occurrences each),
summed medians change from 3,913,196 to 3,912,607 cycles, only 0.015%. Playback remains
218/491, identical to the address-only candidate. This is insufficient benefit to retain
the arithmetic change; the original mask and sign extension remain.

## R3: edge decision

The existing edge arithmetic retains its eight fractional bits, signed divide, overflow
fallback and arithmetic right shift. The 18,746 extraction shifts account for 58,282 cycles,
just 1.441% of baseline fast-raster instruction cycles. Even deleting their entire cost
would save no more than that fraction; replacing them cannot achieve that upper bound.
Changing to a 16.16 accumulator to use SWAP also needs conversion and restoration, and loses
high bits unless bounded or guarded. For example, shifting accumulator `0x00800000` left
eight then restoring with arithmetic right shift produces `0xff800000`, not the original.
Do not narrow the routine's accepted arithmetic domain based only on one clipped route.
This representation change is rejected on the measured small upper bound and extra
correctness burden, without claiming a measured speedup or slowdown for unimplemented code.
Indexed edge stores and DBF account for 530,697 cycles (13.12% of the raster total),
9.1 times the extraction cost; restructuring those would require a separately justified replacement, not a safe local arithmetic edit.

## R4: CPU selection and validation

The 68000 trial produced a worse complete-window result: 87 intervals / 490 fields versus
87 / 465 at baseline (8.878 versus 9.355 fps). Gameplay inputs evolve with timing, so this
does not establish that the local instructions alone became slower. It does fail the
end-to-end acceptance test. The selected implementation therefore preserves the previous
loops on 68000/68010 and selects the refinement only when Exec reports 68020 capability.
This selection happens once during installation; no CPU test is added to the drawing loop.
The current release selector enables this path on 68020+ with real fast RAM. Cache selection remains entirely WHDLoad's responsibility.

The final CPU-selected build passes these 500-field drawing twins:

| CPU / path | Completed staged scenes during capture |
| --- | ---: |
| 68000, preserved loops | 39 |
| 68020, refined loops | 89 |
| 68030, refined loops | 131 |
| 68040-NOMMU, refined loops | 144 |
| 68060-NOMMU, refined loops | 145 |
| 68020 with relocated edge scratch (`CUSTOM2=2`) | 89 |

All 637 completed staged scenes have zero pixel/register/CCR/scratch/guard failures; copied
raster code stays unchanged. The scratch-specific checks are exercised by the separate
`CUSTOM2=2` run; ordinary runs retain native scratch.

`tools/check_raster_layout.py CAPTURE` audits all sixteen colour loops, including unobserved
colours; use `--legacy` for 68000/68010. It checks branch
instruction boundaries, the correct wide/single writer for each colour, empty-row and DBF
destinations, plane pointers, masks, dispatch and the native return sequence. Original span
writer instructions must match the game's untouched chip-memory copy exactly.

### Reproduction

Build and freeze baseline and candidate slaves separately. For the 68020 trace and timing:

```sh
source amiga/env.sh
export AMIGA_MODEL=A1200 CPU=68EC020 KICKSTART="$KICKSTART_A1200"
export CHIP_KB=2048 FAST_KB=4096 EXTRA_ARGS=--slow_memory=0 ANCHOR=0xbc7c
WHD_ARGS='CUSTOM4=1 CUSTOM5=2 NoCache' FIELDS=100 \
  tools/fixed_window.sh tmp/prof/raster-twin tmp/build/Powerdrome-verify.slave
python3 tools/perf_status.py tmp/prof/raster-twin
python3 tools/raster_pairs.py tmp/prof/raster-twin
python3 tools/raster_costs.py tmp/prof/raster-twin
python3 tools/check_raster_layout.py tmp/prof/raster-twin
WHD_ARGS='CUSTOM5=2 NoCache' FIELDS=500 SWAP_ONLY=1 \
  tools/fixed_window.sh tmp/prof/raster-timing tmp/build/Powerdrome-verify.slave
```

For long twins use `CUSTOM4=1 FIELDS=500 SWAP_ONLY=1`; the diagnostic counters still compare
every completed drawing twin without generating a large instruction trace. For 030/040/060
use the CPU, frequency and exact-cycle arguments in `tools/release_matrix.py`, with
`68040-NOMMU` and `68060-NOMMU`. The current selector retains native rendering on 68000/68010; the older 68000
staged-raster trials above are not reachable through the current user options. Each before/after pair must retain the same settings.
All captures use the first driving presentation; pit-departure animation is outside this
raster comparison. Never interpret twin playback rate as game performance.

### Selected-build timing matrix

All rows below compare the same loader and machine with fast rendering and NoCache, over a
500-field window. The selected build includes the 68000/68010 exclusion.
Numbers use complete presentation intervals within the window, not the count of all
marker hits. Later scene inputs can differ when elapsed-time simulation advances differently.

| CPU | Baseline intervals / fields | Selected intervals / fields | Baseline fps | Selected fps | Change |
| --- | ---: | ---: | ---: | ---: | ---: |
| 68000 | 87 / 465 | 87 / 465 | 9.355 | 9.355 | Unchanged; previous loops retained |
| 68EC020 | 218 / 492 | 218 / 491 | 22.154 | 22.200 | +0.20%; repeated exactly |
| 68030, requested 25 MHz | 299 / 498 | 300 / 498 | 30.020 | 30.120 | +0.33% |
| 68040-NOMMU, requested 25 MHz | 410 / 498 | 414 / 498 | 41.165 | 41.566 | +0.98% |
| 68060-NOMMU, requested 50 MHz | 426 / 499 | 429 / 499 | 42.685 | 42.986 | +0.70% |

Every selected-build 500-field presentation sequence repeats exactly: the baseline sequence
on 68000 and the address-only candidate sequence on 020/030/040/060.

These small changes are supported by the matching-geometry raster cost comparison, but are
not claims about physical accelerators or all racing workloads. The existing elapsed-time
simulation, chip copy extent, guard/fallback decisions and WHDLoad cache policy are unchanged.

Phase D also leaves native M1 spans unchanged. The entire mutable dispatch setup
is only 0.181% of track time, so removing branch rewriting alone cannot meet its
3% frame threshold. No qualifying M1 twin result justifies the conditional chip-code
trial; see [A500 measurements](internals.md#a500-and-chip-only-limits).

## R5: selected change

Retain only direct plane-address construction on 68020+. The 68000/68010 use the previous
fast loops, and `CUSTOM1=1` selects native drawing. Endpoint masking and all edge
arithmetic remain native. No cache-control, simulation, clipping, scheduler or presentation
changes are included.

Both normal and VERIFY slave files grow by 100 bytes. The 32,000-byte bitmap, 21,600-byte
chip copy, sixteen 124-byte loop slots, dispatch table, arena reservation and guards retain
their sizes. The added CPU selection runs at installation, not once per polygon or frame.
Final-build validation passes all selected CPU paths. Separate 100-field option-off and
no-fast-memory runs retain every audited native hook byte, with no decoded direct branch
entering a hook interior. The 68000's complete timing sequence is unchanged. This closes
R1–R5; the separate [race/view/effect campaign](gameplay-coverage.md) also passes.

### Local evidence

Ignored captures retain configuration, hashes, memory snapshots, diagnostics and frame
sequences. R1 uses `tmp/prof/raster-r1-twin-020` and `raster-r1-timing-020`; address and mask
trials use `raster-r2-*` and `raster-r2b-*`. The CPU baseline/candidate matrix is under
`raster-r4-*`; selected-build evidence is under `raster-final-*`. These inputs are never
committed. Normal/VERIFY output sizes are 3,988 / 5,216 bytes.

Selected-build SHA-256:

- Normal: `2daa984b39bf2a367feb8d334359139a5f46084d7f31fd6d39a747f1e422dfa1`
- VERIFY: `12af6b96dc10aefeb9026cf8a00a54cb89ae3ea350844859b139d61fa686ba71`
