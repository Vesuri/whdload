# Step 5: tfx.020 on the 040 timing model

Completed. Evidence: `tmp/step5/strict1`, `strict2`, `observer-off`,
`strict-control`, and permissive control `profile2` (paths relative to this harness).
The window remains [2,252) game-vblank increments, the step 4 action flight and
swap-indexed right/release tape. Both strict profiles publish 57 frames (11.4
nominal-PAL fps), matching the step 4 throughput. These are emulator costs, not
Apollo 1240 hardware timings.

## Important correction to the old baseline

Step 4 used FS-UAE's default `fpu_no_unimplemented=false`: the emulator executed
unsupported FPU operations itself. It therefore cannot measure the benefit of
removing FPSP traps. Preserve those historical results, but use
`--uae_fpu_no_unimplemented=true` for subsequent 040 measurements. The private
observer records the actual boolean, not just the requested configuration.
With it enabled, six sites trap 2,394 times in this window; with it disabled,
there are no F-line entries. The corrected tfx.020 row remains 57/250. The other
FPU executable rows have not been remeasured with this setting; their relative
ranking is not established under strict trapping. The integer row is unaffected
by this FPU option. No game, slave, FPSP or shared emulator files were changed.

## Instrument and validation

The frequency-sensitive 040 NOMMU `m68k_run_3ce` loop has no Barto instruction
profiler. A private observer counts every executed PC, actual call target, raw
scheduler ticks, logical chip data accesses, exception site and cache opcode.
It covers all addresses, including Z3; it does not use the 24-bit trace window.
The full source patch is `tools/040-cost-observer.patch`, against the step 4
metadata-only build. Start/stop occur at the same read-only vblank breakpoints
as the baseline. No guest instructions, memory, inputs or cache state are patched.

Self cost comprises instruction fetch/prefetch, execution and the backend's
all-cached instruction padding. `do_specialties` overhead is accounted separately.
No division/rounding is applied to individual instruction times. The sum of all
four buckets equals the start/end scheduler delta exactly: 9,094,528,000 raw
ticks for 42,860,596 instructions, with no unattributed elapsed time. This is
approximately 202.10 million emulated CPU-cycle units at the live divisor 45.
56.41% of this backend's time is synthetic all-cached padding; it does not model
040/FPU instruction latencies accurately. Use costs to choose candidates, and
require measured A/B improvement and eventually hardware confirmation.

- `strict1` and `strict2`: byte-identical PC/count/cost profile; identical events,
  inputs, image, and all entry/start/end game-hunk bytes.
- `observer-off`: same build, observation disabled; identical events, inputs,
  image and every captured game-hunk byte. This isolates observer overhead.
- `strict-control`: older step 4 binary, observation absent; same 57 frames,
  same input delivery and image. Its entry clock is one vblank later (1790 versus
  1789); publications 54/55 occur one vblank earlier, and raw snapshots differ.
  This is retained as a separate control, not a new state-equivalence waiver.
- `observer-validation.json` retains these distinctions. Negative checks reject
  a missing cost tick and a missing FPU exception. Python/shell syntax and patch
  application against the original metadata tree were checked. The final cockpit
  image was visually inspected.

This configuration retains 040/FPU, requested 40 MHz, live cycle divisor 45,
32 MB Z3, 2 MB chip, Kickstart 3.1, WHDLoad 20.1 and CACR $80008000.
The original MMU setup remains for functional regressions, not cost percentages.
The 060 software path is unchanged.

## Cost report

`profile-report.json`, `routine-costs.csv`, and raw `profile.csv` retain every
executed PC and every nonempty routine region. Regions are bounded by observed
call targets and compiler LINK prologues. They are self regions, not inclusive
call-tree timings: callees are charged separately. Jump-dispatched assembler
blocks can share a region; notably the SetColor row includes shape commands.
Step 6's `symbol-map.md` now separates recovered symbol spans, reviewed identities
and local labels, and audits selected function boundaries. The original cost
intervals below remain unchanged; they are not all single function bodies.

Symbol names are hints from unique matching runs of 16 normalized instructions
against the installed TFX.040 code hunks 0/5/6/12/14. Descriptive names for other
hot regions are based on inspected instructions and call sites; they are marked
as such rather than presented as recovered original symbols. No nearest-symbol
name is carried across an unmatched gap. Small unmatched routines retain their
hunk offset as an explicit identity. Every region at or above 0.5% is below;
remaining individual regions are in the CSV.

| Start (hunk offset unless stated) | Region | Self cost |
|---|---|---:|
| `0x6c4f2` | ScanFillDown | 14.826% |
| `slave:$20b8` | do_swap_screen / fast-to-chip screen copy | 12.510% |
| `0x4e53a` | CPU masked sprite merge | 8.713% |
| `0x55e32` | Project | 5.954% |
| `0x5765e` | SetColor / shape command region | 5.729% |
| `0x3b93a` | SuperShape view dispatcher (descriptive) | 5.292% |
| `0x60bfc` | polygon bounds / edge preparation | 3.927% |
| `0x6a4a2` | _qdiv | 2.310% |
| `0x4f54e` | _DrawSpriteImage | 2.308% |
| `0x38236` | @UseLevel | 1.754% |
| `0x4e6b4` | _DrawMonoImage (slave patch anchor) | 1.640% |
| `0x77c8` | aircraft list update loop | 1.576% |
| `0x62408` | _xSuperShapeTranslate | 1.501% |
| `loaded image:$0` | planar image drawing code called at game:$3816 | 1.442% |
| `0x5f252` | left polygon edge generator | 1.128% |
| `0x5f1e0` | right polygon edge generator | 1.107% |
| `0x4bdca` | integer square root | 1.101% |
| `0x249a` | RGB palette blend loop | 1.027% |
| `0xb7c4` | @gbased_move | 0.979% |
| `0x4b774` | matrix angle helper | 0.900% |
| `0x3f51e` | shape handle address lookup | 0.797% |
| `0x5f124` | paired polygon edge walker | 0.749% |
| `0x3bc56` | nested SuperShape dispatcher (descriptive) | 0.720% |
| `0x3d032` | SuperShape part evaluation | 0.693% |
| `0x60b7c` | ConeCheck | 0.647% |
| `0x7d90` | aircraft iterator, table DBF8 | 0.645% |
| `0x30b04` | @flight_computer | 0.617% |
| `0x39cac` | viewport scale calculation | 0.610% |
| `0x62576` | _SuperShapeAddMobile | 0.562% |
| `0x7d54` | aircraft iterator, table DB30 | 0.532% |

Functional shares below are conservative classifications of identified regions.
Projection/geometry used to draw shapes counts as rendering; standalone arithmetic
helpers count as maths. Physics/flight control counts as game logic. Unclassified
small routines remain explicit, so these are not claims that all game logic or
all maths have already been recognized. FPSP is separate from native maths.

| Category | Share |
|---|---:|
| interrupt/other dispatch overhead | 0.008% |
| OS / other | 0.604% |
| FPSP | 0.487% |
| unclassified game | 6.965% |
| rendering | 78.846% |
| game logic | 6.906% |
| maths | 4.312% |
| slave | 1.873% |

## FPSP, chip accesses and cache flushes

F-line exception counts independently agree with executions of FPSP's installed
`_fpspEntry_fline` (FPSP hunk offset $3a00): 2,394. All other installed FPSP
entry points were executed zero times. Loaded FPSP code was located with 277
matching signatures; preload copies with no execution were rejected. Its self
cost is 0.487% in this timing model. Exception setup is charged to the faulting
instruction. This small emulator percentage is not a hardware estimate of FPSP
penalty.

| tfx.020 site | Opcode | Window entries | Per rendered frame |
|---|---|---:|---:|
| `0x50f82` | FTAN | 57 | 1 |
| `0x5169e` | FSIN | 1197 | 21 |
| `0x516b6` | FCOS | 513 | 9 |
| `0x517a4` | FATAN | 228 | 4 |
| `0x517f2` | FATAN | 57 | 1 |
| `0x5183c` | FASIN | 342 | 6 |

`fpsp-per-frame.csv` retains each opcode/site count per publication interval.
Each of the 57 observed intervals has exactly 42 entries. There are zero FINTRZ
or FMOVECR traps in this fixture: existing slave patches cover the executed sites.
That does not prove the other static sites are unreachable in other missions.
There are also 250 level-3, 54 level-2 and 19 level-4 interrupt exceptions.

Logical CPU data operations addressed to chip RAM: **1,032,912 reads** and
**1,249,307 writes**, carrying **2,729,419 read bytes** and **4,656,345 write bytes**.
The four bulk screen-copy MOVE.Ls alone write 3,648,000 bytes, 78.34% of chip-write
bytes. These are logical accesses at the 040 data-cache API, including stack/data
operations; not cache misses, physical bus transfers, instruction fetches or DMA.
They exclude debugger reads. The observer does not alter cache behaviour.
Per-game-region access counts are retained in `routine-costs.csv`; per-PC counters
also cover slave, FPSP and OS. Chip traffic from display DMA is a different metric.

**Zero cache flushes** in the fixed window: no game calls to Exec CacheClearU,
CacheClearE or CacheControl; no slave `_flushcache` entry; no F4xx cache instruction.
`cache-per-frame.csv` preserves zero for every interval, including the initial
partial interval. This is the default new-renderer path, where the slave already
replaces the relevant SMC setup. Do not infer a cache-flush win from the general
SMC comment in the source; other renderer paths/scenes require their own counts.

## Reproduction

From the game directory, build only if the private destination does not exist:

```sh
bash tools/build_profile_emulator.sh tmp/step4-emulator/fs-uae
```

The input must be the configured step 4 metadata observer tree. Build refuses to
overwrite. No changes are applied to shared AmigaXDev or its installed emulator.

```sh
FSUAE="$PWD/tmp/step5-emulator/fs-uae/fs-uae"   python3 tools/profile_flight.py tmp/step5-new --strict-fpu
python3 tools/profile_regions.py tmp/step5-new
python3 tools/profile_symbols.py tmp/step5-new 16
python3 tools/report_profile.py tmp/step5-new
```

Strict comparison (no clock or state waiver):

```sh
python3 tools/check_profile_pair.py tmp/step5/strict1 tmp/step5/strict2
python3 tools/check_profile_pair.py tmp/step5/strict1 tmp/step5/observer-off
```

Use a new output directory. Run again to a different output for a cold-boot pair.
The harness uses the preserved `tmp/step5/seed-strict` and the unchanged step 4
slave/FPSP inputs. Recreate the seed if changing any game/slave/FPSP/startup option;
never reuse it across changed inputs. Local debugger socket access is needed.
Omitting `--strict-fpu` intentionally reproduces the permissive historical control,
not the target-040 trap experiment. The report expects this frozen baseline's
counts and fails on changed coverage/entries; adapt its baseline assertions only
for an explicitly different experiment. Tool snapshots and hashes are retained.

Observer-off control (same strict seed):

```sh
FSUAE="$PWD/tmp/step5-emulator/fs-uae/fs-uae"   python3 tools/baseline_matrix.py --machine 040 --variant newfpu   --output tmp/step5-off-new --seed tmp/step5/seed-strict   --extra-args='--cpu=68040-NOMMU --uae_cpu_cycle_exact=true --uae_cpu_memory_cycle_exact=true --uae_fpu_no_unimplemented=true'
```

## Next: step 6

Transfer and validate symbols properly, including the manual hot-region names and
all paraj patch targets. Keep the profiler's offset identities and observed call
edges as evidence; normalized matching alone is not proof of routine equivalence.
Prioritize ScanFillDown, the screen copy, masked sprite merge, Project, shape
command/edge dispatch, and the six transcendental wrappers. Retain tfx.020 as the
base. Rendering dominates this fixture; the eventual native-FPU correctness goal
still requires eliminating the observed 42 traps/frame and covering other scenes.
No optimization patch was written during this profiling step.
