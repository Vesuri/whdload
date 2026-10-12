# Accelerator and cache testing

Current release status and validation limits are in [open work](open-work.md).

Completion-plan C2 now routes fallback polygons through installed static raster
code on 68020+, keeping their native bitmap pointers. Its M4 departure/track audit
has zero observed game-code writes; pit/title images and M4/M5/M7 twins pass.
This does not change WHDLoad cache selection or certify physical hardware.


Current end-to-end figures and machine configurations are in
[internals](internals.md#current-measurements). Standard WHDLoad `CACHE` and
`DCACHE` options belong to the user; neither build changes cache policy or samples
control registers. Shared KickEmu startup remains unmodified.

Emulator runs do not certify physical accelerator boards or all cache settings.
Physical-board validation is outside the selected scope.

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
Title/pit/unsupported scenes retain native bitmap rendering, but C2 routes their
polygons through static code on 68020+ when that code is installed. Its 200-field
Practice trace reports zero game-code writes. Native self-modification remains
with the option off, on 68000/68010 fallbacks and in deliberate twin references.
The user's cache selection is unchanged.

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

Use `tools/release_matrix.py` as described in [development](development.md#release-matrix).
It freezes each input slave with its capture metadata, uses read-only counters for
throughput, and separately runs renderer twins and a 040 CACHE route smoke.
Requested emulator frequencies are configuration inputs, not physical-board timing
certification. Compare each machine with its own native baseline.

## Emulator cache coverage limits

The available FS-UAE source selects separate MMU execution loops before its cycle-exact
non-MMU loops. In its 040/060 MMU path, `include/cpummu.h` defines `MMU_ICACHE=0`; instruction
fetches use MMU-translated memory reads, and the data access path similarly is not a
physical copyback-cache model. A successful MMU run tests CPU/MMU setup and game logic,
not real 040/060 cache coherency. Its timing must not be compared with the table above.

## Compatibility and release policy

Both the full timing scheduler and fast planar renderer are selected automatically
on 68020+ with real fast RAM. All other machines keep original timing and rendering.
`CUSTOM1=1` and `CUSTOM3=1` independently select original rendering and timing.
Normal builds have no automated input, twin drawing or mismatch fixtures.

Read [open work](open-work.md) for release gate status and remaining limits.
`check_disabled.py CAPTURE --timing` checks original relocated hook bytes in both
initial and final snapshots. `perf_status.py CAPTURE` checks staged renderer
pixels, registers/CCR, scratch, guards and copied-code immutability in twin runs.
The pit/departure/track CACHE smoke checks that the route executes; it is not a
physical copyback-cache coherency test.

## Release twin and smoke results

The current release completes 17 M4 NoCache, 26 M5 CACHE and 29 M7 NoCache twins
without pixel, register/CCR, scratch or guard failures. Their copied code remains
unchanged. M6 CACHE reaches ordered pit/departure/track checkpoints and completes
100 staged scenes with twins disabled; this exercises production static routing.

M7 CACHE twins failed: 50 pixel mismatches during the window, 186 total register
mismatches, first normalized/reference a0 differing by two bytes, and zero guard
or scratch failures. Copied code stayed unchanged. The first failure is already
present at the driving anchor. Its NoCache retry passes all comparison checks.
Evidence remains in `tmp/phase-f/fast-required/M7-CACHE-practice-twins` and
`M7-NoCache-practice-twins`; the failed run is not discarded or counted as a pass.

`VERIFY` twins call `native_poly` for their reference before `routed_poly` draws
into fast memory. That reference executes the original branch-displacement writes;
the installed production path uses static loops. This is a cache-sensitive twin
comparison failure, consistent with the native reference's self-modification.
No particular emulator/cache instruction cause has been isolated. Do not claim
cached pixel equivalence from the passing NoCache twins, cached fps runs or the
production-path smoke. Normal cache selection still belongs entirely to WHDLoad.
