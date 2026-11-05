# Grand Prix Circuit development

Read `docs/open-work.md`, `docs/PERFORMANCE_PLAN.md`, then this file and `docs/internals.md`.
Paths below are relative to the game directory (`games/GrandPrixCircuit`), where every
command runs. The slave source is `src/`; `tools/` is the harness. Phases 0–8 are complete.

The harness was written in the fork worktree's ignored `tmp/dev/` and came in with the move
onto this repository's layout. Its captures and evidence (`tmp/validation`, `tmp/prof`,
`tmp/phase3` .. `tmp/phase8`, `tmp/audio040`, `tmp/menu-*` and the rest) stayed in that
harness: the paths in these docs name directories of the game's ignored `tmp/` that this
repository does not hold. Copying that harness's `tmp/` here restores them; the tools
recreate them otherwise.

## Inputs and environment

`inputs.sha256` pins the installer archive (`GrandPrixCircuit.lha`) and the pre-installed
v1.0 game (`GrandPrixCircuit_v1.0_0008.lha`). `make unpack ARCHIVES=<directory>` checks
them into `tmp/archives/` and unpacks each into a drawer named after it:
`tmp/game/GrandPrixCircuit_v1.0_0008` is the pristine installed game that runs,
`tmp/game/GrandPrixCircuit` the installer package. `python3 tools/check_inputs.py` (run by
`make unpack` and `make check`) checks all 55 installed files, including the outer icon,
against `manifest/GrandPrixCircuit_v1.0_0008.files.json`;
`manifest/GrandPrixCircuit.files.json` lists the installer's members.

The shared environment is `../../common/env.sh` (AmigaXDev's): VASM, WHDLOAD,
WHDLOAD_BINARY, KICKSTART, KICKSTART_A1200, KICKSTART13, RTB, WORKBENCH_ADF, AMIGA_PYLIB.
`game.conf` builds with `-m68000 -pic -x -devpac -Fhunkexe -nosym` against the shared
WHDLoad includes and KickEmu, the shared `lvo/` bridges and the NDK 3.2 `Include_I`
(`NDK`). Some tools read the installed executable from `GPC_GAME` (default
`tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit`); `GAME` is the repository's game
name.

## Build and play

```
make slave                                 # tmp/build/release/GrandPrixCircuit.Slave
make verify                                # tmp/build/verify/GrandPrixCircuit.Slave (-DVERIFY=1)
make verify VERIFY_FLAGS=-DVERIFY_TAPE=1   # the same, with the private tape (Phase 6)
make run                                   # the release build on the A500 profile
make run SLAVE=original                    # the shipped 1.0 slave
make run WHD_ARGS=CUSTOM2=0                # the release build, enhancements off
make run-a1200                             # tools/run-a1200.sh
make run-68030                             # tools/run-68030.sh
```

Machines: the A500 profile (game.conf, `SETUP=custom`) is a 68000 with 512 KB chip +
1536 KB slow RAM and no fast RAM. `make run-a1200` is a 68EC020 with 2 MB chip + 4 MB fast
on Kickstart 3.1; `make run-68030` the same with a cycle-exact 25 MHz 68030. All three
configurations have Phase 2 baselines. The machine variables (`CPU`, `CHIP_KB`,
`FAST_KB`, `SLOW_KB`, `AMIGA_MODEL`, `KICKSTART`, `EXTRA_ARGS`) given in the environment
replace the profile's, which is how the capture tools below select their machines.

Runtime game/Kickstart/WHDLoad copies live in `tmp/run/default/.run/dh0` and `dh1`
(`tmp/run/<INSTANCE>/` for another instance). Pristine inputs are never mounted writable.
The shared process helper owns the port and recorded emulator PID; stop an emulator with
`make stop`, never by name. Debug server: `python3 tools/gpc.py serve` (common/run.sh with
`DEBUG=1` and the run options); commands include stop, cont, shot, gdb, profile and quit.
Without `SLAVE` the server boots the shipped slave (`SLAVE=original`), as the harness's
launcher did; pass `SLAVE=tmp/build/release/GrandPrixCircuit.Slave` (or a capture's slave)
for a build. It works in the game directory, so gdb memory dumps can use space-free
relative paths under `tmp`.

## Phase 1 validation

```
SLAVE="$PWD/tmp/build/release/GrandPrixCircuit.Slave" WHD_ARGS=CUSTOM2=0 WARP=1 \
 python3 tools/validate_boot.py normal --calibrate
# Pass the printed hunk base with --hunk when it differs from the A500 default.
SLAVE="$PWD/tmp/build/release/GrandPrixCircuit.Slave" WHD_ARGS=CUSTOM2=0 WARP=1 \
 python3 tools/validate_boot.py normal --cycles 2
python3 tools/check_disabled.py tmp/validation/normal/race0.bin
python3 tools/check_music.py tmp/validation/normal/title.bin
python3 tools/check_units.py tmp/validation/verify/race0.bin
python3 tools/audit_simulation.py tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/GrandPrixCircuit
python3 tools/check_inputs.py
```

The validator boots at the original game's entry, arms overlay-entry/write breakpoints and
an 834-byte jump-table watch, captures opening and race screens, and checks table stability.
A positive control watches native VBL writes over a range of the same size. Dumps cover
slow RAM by default; set DUMP_BASE=0x200000 DUMP_SIZE=0x400000 for the A1200 and calibrate
its hunk base. Set machine variables as in the wrapper; it does not call run-a1200 itself.
Evidence is in `tmp/validation`, with exact slaves, hashes, logs, metadata and RAM/screens.
The earlier modern run's `title.png` is the black post-intro transition; shipped/unmodified/
VERIFY/A1200/whd19 `title.png` is the visible Accolade opening screen. The car presentations
and cockpit screenshots are also retained under `tmp/build`.

`check_disabled.py` checks all immutable code, known original patches and all jump stubs.
`check_units.py` checks VERIFY discovery metadata only: no rate helpers or rate tests exist.
The music checker validates the live code allocation (cached unpatched files also exist).
`compare_state.py` compares the complete data hunk, with code/data pointer normalization;
it is not a proof of cross-boot determinism. Baseline and modern helper code matches, while
BASM encodings differ in the shipped binary. Only active game pixels, excluding emulator
borders, are meaningful for screenshot identity. No per-field gameplay equivalence claimed.

## Phase 2 captures

Use bash, from the game directory. Fixed-window captures require the
VERIFY build (the default); the debug server still defaults to the shipped slave.
The short trace includes the start-light transition and early acceleration; the longer
counter covers the opening driving section. Both start after 300 native VBLs from the
first race loop, dropping the partial current field. Do not substitute a wall-time wait.

```sh
make verify
export SLAVE="$PWD/tmp/build/verify/GrandPrixCircuit.Slave"
export WHD_ARGS='CUSTOM2=0 CUSTOM3=1 CUSTOM5=1'
FIELDS=100 tools/fixed_window.sh tmp/prof/example-full1
FIELDS=100 tools/fixed_window.sh tmp/prof/example-full2
python3 tools/compare_captures.py tmp/prof/example-full1 tmp/prof/example-full2
python3 tools/trace_metrics.py tmp/prof/example-full1
SLAVE="$PWD/tmp/prof/example-full1/slave.slave" python3 tools/gpc_report.py \
 tmp/prof/example-full1/trace.bin tmp/prof/example-full1/code.bin --base 0xc00000
FIELDS=1000 SWAP_ONLY=1 tools/fixed_window.sh tmp/prof/example-swaps
SKIP_FIELDS=0 INPUT_AUDIT=1 tools/fixed_window.sh tmp/prof/example-tape
WHD_ARGS='CUSTOM2=0 CUSTOM3=0 CUSTOM5=0' FIELDS=100 SWAP_ONLY=1 \
 tools/fixed_window.sh tmp/prof/example-off
python3 tools/check_phase2.py tmp/prof/example-off
python3 tools/audit_simulation.py tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/GrandPrixCircuit
python3 tools/check_inputs.py
```

For expanded A1200 prefix the capture with:
`AMIGA_MODEL=A1200 CPU=68EC020 CHIP_KB=2048 FAST_KB=4096 SLOW_KB=0
KICKSTART="$KICKSTART_A1200"` and use dump base 0x200000 for reports.
For 68030 use the same memory/ROM settings, `CPU=68030`, `SWAP_ONLY=1` and
`EXTRA_ARGS='--uae_cpu_speed=real --uae_cpu_multiplier=0
--uae_cpu_frequency=25000000 --uae_cpu_cycle_exact=true'`. Join these lines in the shell.
Run machines sequentially; the shared debugger port belongs to one emulator at a time.
The 68030 backend supplies no usable instruction trace. CACR is read in the VERIFY
slave on 020+; the 68000 path never executes MOVEC. No cache policy is changed.

Counter validation: compare `metrics.json`'s `swap_pattern` with `swaps.json`'s first
100 entries. `trace_metrics.py` also proves each LoadView publication switches DMA
bitplane buffers on the following field. `frames.txt` retains the donor's game-only
polling statistic; use `metrics.json` for the complete game + KickEmu polling cost.
The normal slave compares byte-for-byte with `tmp/validation/modern/slave.slave`.
All source hooks are VERIFY-only; CUSTOM2 still has no effect.

Final evidence lives in `tmp/prof/phase2-*`: A500 full1/full2/aligned, A1200
full1/full2/swaps, 68030 swaps1/swaps2, tape and fixtures-off. Earlier `p2-*` and
`phase2-a500-swaps` were exploratory or used the superseded field alignment; do not
quote them. PERFORMANCE_PLAN.md and `internals.md` record the final numbers.
`compare_captures.py` compares all instruction/register/cycle and DMA records, active
pixels, and complete data at both boundaries. Relocation normalization is explicit;
there are no arbitrary masks. The 030 repeat compares entire fast-RAM dumps and counts.
Self/inclusive function attribution is heuristic for shared tails/partial calls; inspect
hot instructions and IRQ entry-to-RTE costs before drawing conclusions.

## Phase 3 game time

Authoritative findings and rate inventory: `docs/GAME_TIME.md`. These instruments are diagnostics only; CUSTOM2 still changes nothing.
Final VERIFY SHA-256: `7af8f2f025632252c316c1ef6aa0991b254165edc2fac2d6a14784d41b01d0ed`.
Use only `tmp/phase3/accepted-*` as final evidence; `REJECTED.txt` explains earlier runs.

From the game directory, in bash:

```sh
make verify
export SLAVE="$PWD/tmp/build/verify/GrandPrixCircuit.Slave"
export WHD_ARGS='CUSTOM1=1 CUSTOM2=0 CUSTOM3=1 CUSTOM4=0 CUSTOM5=1'
SKIP_FIELDS=0 PHASE3_FIELDS=720 tools/fixed_window.sh tmp/phase3/example-traffic
WHD_ARGS='CUSTOM1=1 CUSTOM2=0 CUSTOM3=1 CUSTOM4=1 CUSTOM5=1' \
 SKIP_FIELDS=0 PHASE3_FIELDS=720 tools/fixed_window.sh tmp/phase3/example-slow
python3 tools/phase3_compare.py tmp/phase3/example-traffic tmp/phase3/example-slow \
 --out tmp/phase3/example-comparison.json
SKIP_FIELDS=0 PHASE3_FIELDS=120 tools/fixed_ticks.sh tmp/phase3/example-completed-ticks
SKIP_FIELDS=600 FIELDS=100 tools/fixed_window.sh tmp/phase3/example-cost
python3 tools/step_cost.py tmp/phase3/example-cost
python3 tools/check_phase3.py tmp/phase3/example-cost
python3 tools/check_inputs.py
python3 tools/audit_simulation.py tmp/game/GrandPrixCircuit_v1.0_0008/GrandPrixCircuit/data/GrandPrixCircuit
```

Set CUSTOM1=0 for the original solo attract case. CUSTOM1=1 explicitly supplies the
qualifying setup with a grid permutation before native initialisation; this is an artificial
attract-with-traffic fixture, not a UI race. The wrapper rejects duplicate/uninitialised
car IDs/positions before recording. An opponents flag alone is insufficient: qualifying
leaves the grid order zeroed, causing ten copies of the player slot and backwards collision
corrections. Those initial runs are discarded. CUSTOM4 now waits only after the first race
anchor, so it does not change the initial simulation phase by delaying the setup draw.

For A1200 use the Phase 2 machine environment prefix. Run captures sequentially. The
metadata records the exact options, epoch, code/data bases, cache state and slave hash.
`phase3_fields.py` reads all `$9364` allocated hunk-1 bytes at successive native VBL entries,
counts steps at `$7754` and publications at `$39e`. `phase3_ticks.py` instead reads at
`$7762` only after a `$7754` step (skipping lightweight callbacks). Neither writes game
state. `phase3_compare.py` retains every whole-data difference and separately decodes
named quantities, including input, lap/race state and nine opponents; track positions are
relative to the native track-origin pointer. `phase3_summary.py tmp/phase3` checks period,
populated moving opponents and summarises all accepted capture directories.

`step_cost.py` sums instruction records from native VBL entry through its RTS. It includes
callees, but not outer interrupt dispatch or unrelated interrupt handlers. It checks
non-reentry and reports nine native opponent updates in every accepted priced traffic
step. Its period projections include non-step callback overhead and are not guarantees
about future helper overhead or worst-case driving.

The corrected allocation extent also applies to `state_fields.py`, `gpc_report.py` and
`compare_state.py`. `$8918` is only the initialised payload; the hunk header allocates
`$9364`. Old short state captures are readable but do not contain BSS race controls.
Phase 2's whole-RAM before/after dumps retained them: corrected two-boot comparisons pass
for both A500 and A1200 (`phase2-bss-recheck-*.txt`). No arbitrary comparison masks were added.

Hook audit: eight complete spans; the linear disassembler's apparent BCC at `$263c` is
inside adjacent `%ld` and `Lap Number` text. The audit verifies the exact string bytes
before excluding that single false instruction. No executable branch into a hook interior
was found. The slow helper preserves d0/d1 and X before replaying both native calls;
the traffic helper preserves d0/a0 and X, and its final flag result is overwritten by the
first MOVE in the immediately following native `$53ce` call. Normal builds have neither hook.

## Phase 4 review measurements

No slave rebuild or source change. Use the retained final Phase 3 VERIFY binary.
From the game directory, reproduce the 50 MHz run with `hz=50000000` and output
`tmp/phase4/68030-50-1`; reproduce both 100 MHz boots with `hz=100000000` and outputs
`tmp/phase4/68030-100-1` and `tmp/phase4/68030-100-2`. Use new output names if retaining
an existing capture. Run captures sequentially:

```sh
. ../../common/env.sh
hz=100000000
AMIGA_MODEL=A1200 CPU=68030 CHIP_KB=2048 FAST_KB=4096 SLOW_KB=0 \
KICKSTART="$KICKSTART_A1200" \
EXTRA_ARGS="--uae_cpu_speed=real --uae_cpu_multiplier=0 --uae_cpu_frequency=$hz --uae_cpu_cycle_exact=true" \
WHD_ARGS='CUSTOM1=0 CUSTOM2=0 CUSTOM3=1 CUSTOM4=0 CUSTOM5=1' \
SKIP_FIELDS=300 FIELDS=1000 SWAP_ONLY=1 SERVE_WAIT=600 \
tools/fixed_window.sh tmp/phase4/68030-100-2
python3 tools/review_phase4.py
python3 tools/check_phase3.py tmp/phase4/68030-100-2
python3 tools/check_inputs.py
```

`review_phase4.py` computes exact publication rates and checks the fastest pair's entire
1,000-field count series, metadata and complete game code/allocated-data hunks at both
boundaries. It also reports every difference in the full 4 MB dumps; it does not require
unrelated memory outside the game hunks to match or hide those differences. The final policy and
limitations are in the tracked Phase 4 review. No 030 instruction-cost inference, cache
change, renderer patch or period-1 implementation is part of this review.

## Phase 5 display and blitter checks

Build normal and VERIFY with `make slave` and `make verify`. From the
game directory, `python3 tools/phase5_matrix.py` runs the five 100-field traces and the
18-run, 1,000-field matrix sequentially with a 600-second deadline per capture. Its
three arms use CUSTOM2/CUSTOM4 = 0/2 (original swap), 0/0 (fixed), 1/0 (enhanced); all
use CUSTOM1=0 CUSTOM3=1 CUSTOM5=1 and 300 warm-up fields. CUSTOM4 is now a bit field:
bit 0 is slow drawing; bit 1 bypasses only the four display hooks. Do not overwrite
accepted capture directories when experimenting; change the output root first.

For each trace, run `tools/buffer_audit.py CAPTURE`, `tools/visual_audit.py CAPTURE`,
`tools/render_flags.py CAPTURE` and `tools/trace_metrics.py CAPTURE` with the shared
Python. The buffer audit checks CPU and blitter D writes against actual bitplane fetch
addresses, distinguishes before-fetch writes and changed words, and retains all results.
The screenshot audit compares the horizon only when the displayed plane set is unchanged.
The register audit reads DMA-observed DMACONR/INTENAR values rather than assuming options
were applied. `tools/review_phase5.py` verifies the two-boot count and complete game-hunk
repeats, A500 noise allowance, optional gains and fixed-trace assertions. Run
`tools/check_phase5.py CAPTURE` for exact original-code/JOTD/stub checks and its corruption
negative control, and `tools/check_inputs.py` for the pristine manifest.

`tools/phase5_lifecycle.py` is a read-only normal-build check. Set SLAVE to the absolute
normal slave, WARP=1 DETERMINISTIC=1 JOY0=none JOY1=none, CELL and CUSTOM2_VALUE (0 or 1),
WHD_ARGS='CUSTOM2=0' or 'CUSTOM2=1', and the usual machine variables. Accepted cells are
CELL=a500-off (68000, 512 chip/1536 slow) and CELL=a1200-on (68EC020, 2048 chip/4096 fast).
It calibrates loaded addresses, boots anew, captures intro/attract screenshots, then follows
the native attract-race exit and checks the pending handoff is cleared. Pause and normal
program-return restoration have static coverage only. Do not use GDB writes for stimulus:
Barto silently drops them. Rejected prototype and write-probe records are named in
`tmp/phase5/REJECTED.txt`. No performance figure comes from these normal smoke tests.

## Phase 6 simulation validation

Build normal with `make slave`; build the instrumented tape candidate with
`make verify VERIFY_FLAGS=-DVERIFY_TAPE=1` (it replaces the plain VERIFY slave in
`tmp/build/verify/`). The tape include is local:
`tmp/include/phase6-tape.bin`, SHA-256
`c0de2436d70e4457aab80ad489b14c42654b3633643279d41c5a3b19e7d4eeb5`.
It was recorded by joystick-only pilot `pilot-record-v2`; no game-state writes are
used for driving. A plain VERIFY build without VERIFY_TAPE assembles a zero tape
and can still run the short fixtures; it cannot reproduce the recorded full lap.

From the game directory, run captures sequentially in fresh directories:

```sh
SERIES=matrix-v5 MATRIX=handling python3 tools/phase6_matrix.py
python3 tools/phase6_compare.py tmp/phase6/matrix-v5-native tmp/phase6/matrix-v5-p6 --assert-core --output tmp/phase6/matrix-v5-native-oracle.json
python3 tools/phase6_review.py tmp/phase6 handling
SERIES=events-v5 MATRIX=events EVENT_AUDIT=1 python3 tools/phase6_matrix.py
python3 tools/phase6_review.py tmp/phase6 events
python3 tools/phase6_final_matrix.py
```

The matrix script uses explicit model/RAM/CPU/options. It discovers the loaded
address on a calibration boot; BOOT_HUNK may bypass calibration only when the
actual loaded address is subsequently verified. RESUME=1 reuses completed event
or handling captures only after checking build hashes, options, sample counts and
guest assertions. Explicit debugger transfer failures get bounded fresh-boot
retries with the rejected attempt preserved. Other failures stop the sequence.
Do not start another emulator or rebuild the binaries while any capture is live.

Final matrix runs A500 period 6 and 68030/25 periods 6/2, then 100-field traffic
instruction/DMA windows on A500 and 020 (also 020 overheat/spin), then normal-build
A500-off and A1200-on title/race/exit checks. Compare core-a500-p6 and core-030-p6
against matrix-v5-p6, and core-030-p2 against matrix-v5-p2 using
`phase6_compare.py --assert-core`. Track pointers are normalized only when they
actually point into the game data allocation; inactive literal sentinels remain
literal and are compared. Every named AI slot is retained.

For full laps use the A1200 model environment, CUSTOM1=0 CUSTOM2=1 CUSTOM3=1,
CUSTOM4=4 or 0, CUSTOM5=23, SKIP_FIELDS=0 PHASE3_FIELDS=10000 LAP_ONLY=1 with
`tools/fixed_window.sh tmp/phase6/lap-final-p6` or `lap-final-p2`. The sparse
sampler records every sixth native field and retains the true field counter;
finish may be observed up to five fields later. Compare completed lap ticks and
matched native fields with `phase6_lap_report.py`, not wall-clock time or callback
counts. The original-period oracle additionally compares all named core values
at matched fields against the retained original pilot recording.

Acceptance bounds are in `tmp/phase6/acceptance.md`. Pit service uses the native
elapsed-fields/6 result; screen-redraw latency is reported separately. Compare
post-return clocks/player state at equal active times as well as reporting the
raw return markers. The final event candidate returns one video field earlier
at period 2; service entry/exit and 52 service ticks match.

`phase6_units.py` reads the private assertion result (final candidate 51/0).
`check_phase6.py` checks exact enabled hook targets/padding and untouched code,
JOTD patches and all 139 stubs, plus a negative corruption control.
`audit_simulation.py` checks instruction boundaries/direct branch entries.
`phase6_step_cost.py` prices complete native callbacks including their callees;
its projections exclude outer IRQ dispatch/audio and are not an FPS claim.
`phase6_latch_audit.py` rejects any foreign instruction during the protected native
copy, independently of VBR, and separately records inclusive Disable/Enable cost.
`buffer_audit.py` records CPU/blitter writes against actual display fetches; inspect
its result and require zero display writes. Visually inspect normal title/race
captures. Pristine input membership and hashes are checked by `check_inputs.py`.


## Phase 7 fractional rendering

The authoritative `render-subunit.s` latches presentation pose with the existing
simulation snapshot, then rebuilds projection tables outside Disable/Enable.
`render-verify.s` supplies 12 additional guest assertions (63 total) and frozen
poses. C4 bit3 selects a frozen pose; bits5–7 select scene0..7 (track offset
32+64*scene), bits8–15 select fraction0..255. C1=1 supplies traffic. The zero
fixture also forces native integer angular lookup and clears alternating wheel
history. This is the zero-added-fraction oracle, not a promise that every native
curve angle has a zero fractional byte during ordinary play.

Canonical main/mirror Y and segment lengths are copied from loaded game data.
Only nine Y boundaries and their affected row maps change for F<256; the native
projection selection list is retained exactly. Front cars already subtract the
camera in their native Q8 relative depth, and must interpolate canonical tables.
Mirror car depth has no extra -1 segment. Near-car setup includes the native
8f92 add16 bias. Signed angular neighbours -88..88 are decoded once into 177
words; interpolation uses floor-index neighbours, including negative angles.
This avoids the cost spikes of a per-angle cache on long curves. The cache
candidate exceeded the budget (3.617% at skip6000) and is not acceptance evidence.

Current final capture prefix is `accepted-` under `tmp/phase7`. Older `final-*`,
`linear-*`, `moving-v7-a500` and earlier candidates are diagnostics, not final acceptance.
`phase7_render_matrix.py` runs four same-build C2off/on zero-fraction pairs and
four nonzero scenes. `phase7_pixels.py` compares every fetched word of all five
planes on every field: 40000bytes/frame, no crop/tolerance/masks. Its changed-byte
negative control uses the same equality predicate. `phase7_tables.py` checks all
256 projection fractions and all45057 clamped signed angles against an independent
magnitude/sign model, and checks guest tables and unchanged native selection bytes.

`phase7_state_matrix.py` compares720native fields to Phase6 on A500,68EC020,030,
and020traffic. LATCH_AUDIT=1 adds read-only debugger observations of render latches
and physics ticks; it does not modify game memory. No temporal interpolation is
needed when every draw has at least one intervening physics step. Do not infer
that result for unmeasured hardware or higher render rates.

Moving cost uses the private original joystick recording, C5=23, C3=1, C2=1,
100fields after skips2000/4000/6000, with an additional C1=1 traffic window.
`phase7_cost.py` counts the entire new helper PC range, including replacement
work and VERIFY branch overhead; it does not subtract native instructions or
claim an FPS improvement. `phase6_latch_audit.py` checks protected copies for
foreign PCs. Require display_writes=0 from buffer_audit, not merely its exit code.
The 030 backend does not provide CPU instruction records; use its read-only state
cadence, not an invented030CPU-cycle figure.

Production smoke checks use `phase5_lifecycle.py` with OUT_ROOT=tmp/phase7,
normal slave, A500 C2off/on and A1200 C2on. Inspect intro/race screenshots and
native race-exit handoff. `phase7_completion.py` binds all final captures to the
normal/tape binary hashes, checks their gates, audits normal runtime code,
records source hashes and rechecks all55pristine manifest entries. Source and
normal/tape binaries rebuild exactly in independent output directories. Ordinary
VERIFY builds without the private tape include; tape VERIFY requires a local
copy of `phase6-tape.bin` in the ignored `tmp/include/`.


Lifecycle: the game calls `$2b5e` again when starting another race, not just at
program boot. C2 hook `$9ee` restores canonical main/mirror/length tables before
that initializer and marks render_fraction=-1 so the next draw updates projection.
Do not hook `$2ba4` across `$2ba8`: the latter is an internal mirror-table loop
entry. `audit_simulation.py` checks that boundary. `SECOND_RACE=1` in the normal
lifecycle tool waits for the real next native initializer, compares all102restored
words, checks cache invalidation and renders40more swaps. It never writes game RAM.

Panorama precision: native821a shiftsheadingby6bits (roadlookupused8). Native
segmentcurveadds at79a0and7a76cancel in curveSum-yaw. Keepthisfullworddifference
latched; addinganothercameraF*curve termwoulddoublecountthesegmentrotation.
