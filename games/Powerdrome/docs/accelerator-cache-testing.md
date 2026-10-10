# Accelerator and cache testing

The fast planar renderer benefits the tested 68030, 68040 and 68060 emulator configurations.
Global cache enablement is unsafe: the native polygon fallback still rewrites branch
instructions. The normal slave therefore retains its existing cache policy. A VERIFY-only
`CUSTOM3=1` experiment isolates caches to expansion and slave memory, leaves chip memory
non-cacheable, and disables the 68060 branch cache.

These results cover emulated Practice departure and driving. They do not certify an
accelerator board, its memory controller, DMA/cache coherency or untested gameplay routes.

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
The fallback is still needed for title/pit/unsupported scenes, so immutable fast code alone
cannot justify caching the whole game.

A static review of absolute writes also found embedded mutable data, including the word at
`$17510` and audio state near `$17b18`, `$17efa` and `$18036`. Data inside a code hunk is not
itself self-modifying code. The observed execution overlap separates these cases.
The audit covers game-origin writes in the recorded routes; it does not prove that all
unexecuted effects, opponent paths or writes by OS/slave code are free of self-modification.

Installation constructs the fast loops and native trampolines before the final
`resload_Patch` cache flush. The cache experiment runs after installation and all route
patches, and `resload_SetCPU` flushes caches on return. No runtime instruction patch was
introduced by the cache experiment.

## Loader correction exposed by MMU testing

Both cache-enabled and cache-disabled 68030 MMU boots exposed an invalid command-line
pointer at the game entry. The loader jumped into the DOS program with `a0` and `d0` left
by `resload_Patch`, whose API permits those scratch registers to be destroyed. The native
entry stores them at `$4944` and `$4948`; `$519a` later dereferences the pointer when the
length is nonzero. Diagnostic boots found poison values, including `$AAAAAAAA` and
`$A0A0A0A0`, and terminated with an access fault before departure.

The loader now supplies an explicit empty command line: a valid newline buffer in `a0`
and zero length in `d0`. This correction applies to normal and VERIFY builds and does not
change renderer selection or simulation timing. Cache reports check that the game's saved
argument length is zero. The timing matrix below uses the corrected loader and final verifier.

## Cache policy under test

The experiment requests `Base_NC | Exp_CB | Slave_CB | IC | DC`, with the full SetCPU mask.
Branch caching, store buffering and superscalar dispatch are not requested. This differs
from KickEmu's `CACHE` preset, which also enables the 68060 branch cache. That cache is
independent of MMU page cache inhibition, so it is unsafe for the native branch rewriting.
Without an active MMU, WHDLoad cannot apply different cache policies to different memory
regions and disables caches for this mixed policy. See
[WHDLoad cache handling](https://whdload.de/docs/en/cache.html) and the
[SetCPU contract](https://whdload.de/docs/autodoc.html#resload_SetCPU).

The reserved expansion arena keeps the original game hunk and DMA assets in chip memory.
Only the CPU bitmap, immutable rasterizer, slave and emulated OS use cacheable expansion.
The CPU reads its fast bitmap and writes the native chip back buffer; DMA never reads the
fast bitmap. Keeping chip data non-cacheable avoids a dirty cached destination awaiting
writeback when the copper/bitplane DMA consumes it.

`tools/cache_status.py CAPTURE` reads the VERIFY diagnostic record: requested policy,
SetCPU's returned policy, Exec CPU flags, CACR and translation-control register. It checks
that the record stays unchanged and rejects an enabled 68060 branch cache. The register
sample is taken at startup, not continuously. The report also reads the captured emulator
configuration: a `-NOMMU` 040/060 model retains TC writes even though its MMU execution
engine is disabled. The TC enable bit alone must not be treated as proof of translation
in that model. Merely seeing cache-enable bits is insufficient:
the MMU page policy determines which accesses can actually be cached.

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

Each completed cache check below covers 500 PAL fields from the first departure iteration
(`$14764`), using pure-drawing twins. All reported **zero pixel, register/condition-code,
scratch and guard failures**, with unchanged copied code and empty launch arguments.
Completed-scene counts exclude the scene still in progress at each capture's end.

| Configuration | Completed staged scenes | SetCPU policy | CACR | TC |
| --- | ---: | --- | --- | --- |
| 68030 MMU, cache-disabled control | 106 | `$0` | `$2000` | `$80c07760` |
| 68030 MMU, isolated caches | 117 | `$33d` | `$2111` | `$80c07760` |
| 68040 MMU, isolated caches | 114 | `$33d` | `$80008000` | `$8000` |
| 68060 MMU, isolated caches | 114 | `$33d` | `$80008000` | `$8000` |
| 68030 without MMU use, isolated caches requested | 106 | `$33d` | `$2000` | `$0` |
| 68040 MMU, `NoCache` override | 114 | `$0` | `$0` | `$8000` |

The 030 without MMU translation retains the requested policy but leaves instruction/data
caches disabled. `NoCache` overrides the requested cache policy on the 040. The 060 branch
cache remains disabled. These are functional results; twin rendering and the MMU execution
model make their frame rates unsuitable as accelerator performance measurements.

`tools/accelerator_matrix.sh timing NEW_OUTPUT [VERIFY_SLAVE]` reproduces the uncached
matrix. Its `cache` mode runs MMU twins on 030/040/060 plus no-MMU and NoCache controls,
stopping on a diagnostic failure. Build with `make -C whdload verify` first. Captures retain
a frozen slave, configuration, memory, counter output and a final screenshot. Reuse a
new output directory for each matrix. Hardware comparisons require the actual boards.

## Uncached timing matrix

Each row uses a fresh boot, A1200 chipset configuration, 2 MiB chip and 4 MiB fast RAM,
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

Physical-board validation is outside the selected project scope. Results remain emulator-only,
and the cache experiment remains VERIFY-only. Any future real-board sign-off would require
separate runs on 68030/040/060 machines with their actual
memory and cache configurations. Record board/clock, chip and fast RAM, WHDLoad version,
MMU use, cache options and slave hash; compare option off/on from the same Practice route.
Run the VERIFY drawing twins first, then measure the non-twin build. Check title/pit/native
fallbacks, cockpit seams, effects and return to pit as well as normal driving. Preserve
`NoCache` as a fallback and do not enable `Cache`, `DCache` or `BranchCache` globally on the
basis of this emulator evidence.

## Compatibility and release policy

The final VERIFY build passed 500-field departure twins on 68000 (24 completed staged
scenes) and 68EC020 (66), with zero pixel, register/flag, scratch or guard failures and
unchanged fast code. The original slave still rebuilds byte-identically against the
installed reference. All three final accelerator option-off captures retain the native
performance-hook bytes. A 100-field 68000 check with 512 KiB chip and 1,536 KiB slow RAM
(no fast RAM) also retains every native hook and performs zero staged renders.

The normal build was also booted to the native name-entry screen on 68000 and 68EC020.
It includes the launch-argument and return-pointer corrections, but no cache
experiment, automatic input, twin drawing, control-register diagnostics or mismatch buffers.
`CUSTOM1=1` remains the only exposed performance toggle, off by default. No simulation
scheduler, timing clamp or rendering order was changed.
