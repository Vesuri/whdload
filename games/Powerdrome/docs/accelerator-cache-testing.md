# Accelerator and cache testing

Project status: completion-plan Phase C is in progress. Phases A and B are complete.
See the [current handoff](open-work.md) for completed checks, open gates and resume priorities.

Current selected-path timings, including the completed local raster refinement, are in the
[raster report](raster-improvements.md). The matrix below isolates the preceding base implementation.

The fast planar renderer benefits the tested 68030, 68040 and 68060 emulator configurations.
Cache selection belongs to the user's standard WHDLoad `CACHE` and `DCACHE` options.
Neither normal nor VERIFY builds add a custom cache policy, cache toggle or control-register
sampler. Shared KickEmu startup is unmodified. The timing runner supplies `NoCache` only to
make its uncached benchmark configuration explicit.

These results cover emulated Practice departure and driving. They do not certify an
accelerator board, every user-selected cache configuration or untested gameplay routes.
Physical-board validation is outside the selected project scope.

## Native code modification audit

`tools/audit_code_writes.py CAPTURE` decodes executed game instructions, evaluates their
memory destinations from the recorded input registers, and intersects written bytes with
executed instruction bytes. It includes register-indirect and indexed destinations, rather
than searching only absolute writes. It rejects unhandled memory-writing instructions.
The initial memory snapshot supplies instruction bytes; the observed branch-displacement
changes do not alter the decoding of memory-write instructions.

| Capture | PAL fields | Distinct executed game instructions | Writes to each branch word |
| --- | ---: | ---: | ---: |
| Native Practice departure repeat | 500 | 4,245 | 1,592 |
| Fast renderer with native drawing twins | 500 | 4,244 | 1,545 |
| Native title demo | 100 | 1,377 | 460 |

All three reported only these instruction modifications, with no unhandled memory operations:

| Writer offset | Destination offset | Meaning |
| --- | --- | --- |
| `$16012` | `$16080–$16081` | Displacement of the branch at `$1607e` |
| `$1601c` | `$1608a–$1608b` | Displacement of the branch at `$16088` |

The twin capture intentionally exercises the native writers as its reference. The copied
fast rasterizer uses fixed span loops and remains byte-identical across its captures.
The fallback is still needed for title/pit/unsupported scenes. The audit describes where
native self-modification remains; it does not change the user's cache selection.

A static review of absolute writes also found embedded mutable data, including the word at
`$17510` and audio state near `$17b18`, `$17efa` and `$18036`. Data inside a code hunk is not
itself self-modifying code. The observed execution overlap separates these cases.
The audit covers game-origin writes in the recorded routes; it does not prove that all
unexecuted effects, opponent paths or writes by OS/slave code are free of self-modification.

Installation constructs the fast loops and native trampolines before the final
`resload_Patch` cache flush. No additional game-specific cache configuration is applied.

## Loader correction exposed by MMU testing

Both cache-enabled and cache-disabled 68030 MMU boots exposed an invalid command-line
pointer at the game entry. The loader jumped into the DOS program with `a0` and `d0` left
by `resload_Patch`, whose API permits those scratch registers to be destroyed. The native
entry stores them at `$4944` and `$4948`; `$519a` later dereferences the pointer when the
length is nonzero. Diagnostic boots found poisoned register values and terminated with an
access fault before departure.

The loader now supplies an explicit empty command line: a valid newline buffer in `a0`
and zero length in `d0`. This correction applies to normal and VERIFY builds and does not
change renderer selection or simulation timing. The timing matrix below uses the corrected
loader and verifier.

## Current validation status

The verifier retains exact raw register matches before translating possible relocated
pointers. This avoids false positives when a word-sized arithmetic result retains high
bits from an earlier pointer: in the first captured failure, native and fast `d3` were
identical, and only the verifier's address-range heuristic changed the comparison value.
The raw fast outputs returned to the game are unaffected by this verification correction.
A separate empty-scanline case leaves `a4` pointing at the colour table at game `$15e68`.
Return-value normalization now translates that relocated code pointer as well as the
mask-table pointer in `a1`. The original polygon's coordinate and rasterizer registers are
otherwise compared exactly, with only documented pointer relocation allowed.
The first failing normalized/raw/reference/input snapshots are retained in VERIFY builds
and decoded by `tools/perf_status.py`.

`tools/accelerator_matrix.sh timing NEW_OUTPUT [VERIFY_SLAVE]` runs the uncached timing
matrix. Build with `make -C whdload verify` first. Captures retain a frozen slave,
configuration, memory, renderer diagnostics and a final screenshot. Reuse a new output
directory for each matrix.

## Uncached timing matrix

The measurements below were captured at revision `4c79767`, before removal of the VERIFY
cache experiment. They have not been remeasured for the current build. Each row uses a fresh
boot, A1200 chipset configuration, 2 MiB chip and 4 MiB fast RAM,
real-speed cycle-exact settings, no JIT, and the same frozen VERIFY slave. `CUSTOM5=2`
selects Practice. The window begins at the first normal driving presentation (`$bc7c`),
and the read-only breakpoint counter runs for 500 PAL fields. FPS uses complete
presentation intervals only. Simulation remains the native elapsed-time-driven loop.

| CPU configuration | Native intervals / fields | Fast intervals / fields | Native fps | Fast fps |
| --- | ---: | ---: | ---: | ---: |
| 68030, requested 25 MHz | 194 / 496 | 299 / 498 | 19.56 | 30.02 |
| 68040 without MMU, requested 25 MHz | 178 / 497 | 410 / 498 | 17.91 | 41.16 |
| 68060 without MMU, requested 50 MHz | 178 / 497 | 426 / 499 | 17.91 | 42.69 |

Frequency sanity checks with fast rendering and requested 8 MHz measured:

| CPU configuration | Intervals / fields | Nominal PAL fps |
| --- | ---: | ---: |
| 68030 | 210 / 497 | 21.13 |
| 68040 without MMU | 367 / 497 | 36.92 |
| 68060 without MMU | 367 / 497 | 36.92 |

All nine timing captures confirm instruction/data caches disabled. The 030 TC is zero;
the 040/060 retain TC `$8000`, but their explicit `-NOMMU` configuration disables emulator
translation. Their frequency checks therefore exercise the non-MMU execution path.

The requested frequency affects each configuration. This is a sanity check, not cycle
accuracy certification. The 040/060 native results are identical in this window, and their
8 MHz fast results are also identical: the emulator shares execution infrastructure and
chip-bus limits. These figures cannot rank real accelerator boards or predict their gains.

## Emulator cache coverage limits

The available FS-UAE source selects separate MMU execution loops before its cycle-exact
non-MMU loops. In its 040/060 MMU path, `include/cpummu.h` defines `MMU_ICACHE=0`; instruction
fetches use MMU-translated memory reads, and the data access path similarly is not a
physical copyback-cache model. A successful MMU run tests CPU/MMU setup and game logic,
not real 040/060 cache coherency. Its timing must not be compared with the table above.

## Compatibility and release policy

The current VERIFY build passed a 500-PAL-field 68EC020 Practice departure run with
`CUSTOM1=1 CUSTOM4=1 CUSTOM5=2 NoCache`: 66 completed staged scenes, zero pixel,
register/CCR, scratch or guard failures, and unchanged copied code. Evidence is retained
in `tmp/prof/cache-removal-twin-020-500`. Normal and VERIFY builds both compile without a
cache experiment record or CUSTOM3 toggle. The normal build remains byte-identical to
the previously validated normal build.

The VERIFY build at revision `4c79767` passed 500-field departure twins on 68000 (24 completed staged
scenes) and 68EC020 (66), with zero pixel, register/flag, scratch or guard failures and
unchanged fast code. The original slave still rebuilds byte-identically against the
installed reference. All three final accelerator option-off captures retain the native
performance-hook bytes. A 100-field 68000 check with 512 KiB chip and 1,536 KiB slow RAM
(no fast RAM) also retains every native hook and performs zero staged renders.

The normal build was also booted to the native name-entry screen on 68000 and 68EC020.
It includes the launch-argument and return-pointer corrections, but no custom cache
policy, automatic input, twin drawing, control-register diagnostics or mismatch buffers.
`CUSTOM1=1` remains the only exposed performance toggle, off by default. No simulation
scheduler, timing clamp or rendering order was changed.
