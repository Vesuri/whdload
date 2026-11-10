# Where this comes from

This game's history is the `4dsportsdriving` branch of the JOTD fork
(Vesuri/jotd_whdload_slaves), the full development history and verification source
(86b353f there), imported here; its ignored harness (`tmp/dev`) became `tools/` and `docs/`.
Commit hashes in these docs are the fork branch's. The fork's `4dsportsdriving-merge`
holds the cleaned production source in one commit (060c1dc), submitted upstream as PR #36
(PR #26 is superseded and closed); upstream has not merged it.

The release here is built from this development source: `make slave` gives the
production SHA256 below (37440 bytes). The cleaned PR build is a different binary
(37344 bytes, SHA256 `ed819a7ed650a23b4f5b05bf18095dbbbd2ef57d646108f04972903e21b1a997`),
and the fork's earlier local testing archives hold that one.

Paths under `tmp/` (captures under `tmp/prof/`, fixtures, emulator builds) name the
fork harness's ignored `tmp/dev/tmp/`; they were not imported and stay there. Rebuild or
recapture them here under this game's `tmp/`.

# 4D Sports Driving current state

`docs/smooth-play-plan.md` is authoritative.
P1-P7 are complete. P6 unifies the production build and refreshes validation,
documentation and the local testing archive. A4000 remains experimental by user
decision: the frozen handling gate is 27/29. The A500 9.5-10 FPS target is deferred.

The release is 4D Sports Driving Enhanced 2.0b (13.10.2026), a beta: `make dist` packages
it, and the installed icon enables Enhanced framerate (CUSTOM2=1). Its evidence is
emulator measurement only; no real-hardware play-test is recorded.

## P7 integrated

P7 is complete under the user's accepted experimental27/29 decision. Both screened
A4000 changes are integrated for both cars, without tuning. All795 live body records
match the offline candidate in each start position. CommonY1442 and commonSpeed7719
remain failed; commonPitch11 passes. Phase failures are53/70/69. Criteria unchanged.

Replay ABI10 rejects older A4000 recordings. Fresh save/load matches1510 semantic
bytes at1500/1550/1600 plus1802 route bytes; native10/20 match1120 bytes at tick200.
The38 disabled ranges and hook audit pass. Opponent crash/restart/finish passes on
D/E without overflow (D196.60s, E86.54s with shortened idle prelude). FULL FPS is
D41.19/E45.39 against the plan's45.29/45.49; the lower040 result is recorded, not tuned.

Evidence: `tmp/prof/p7-integration/validation.json` and `tmp/prof/p7-live/`.
The authoritative P7 section records measured scope and the accepted remaining limits.
No further P7 candidate is pending. The local v2.0b archive is rebuilt, not published.

## Build and play

Run commands from the game directory (`games/4DSportsDriving`); `make unpack
ARCHIVES=<directory>` installs the two pinned archives first. `make slave` builds the
production slave, `tmp/build/release/4DSportsDriving.Slave`; no VERIFY, fixtures or
startup tests. `make verify` is the default VERIFY build (`VERIFY=1`) and
`make build BUILD=manual` the `SIM_MANUAL=1` one. `tools/build.sh` builds every other
fixture combination from its variables (`VERIFY=1 SIM_A4000=1 tools/build.sh`) into
`tmp/build/4DSportsDriving[-suffix].slave`, the names the tools read; without variables
it is the production build. The former `SIM_RUNTIME=1` spelling selects the same build.
There is no separate supported runtime binary.

`make run WHD_ARGS="CUSTOM2=1"` launches the production slave as the installed icon
runs it (the installer writes CUSTOM2=1); `make run SLAVE=original` boots JOTD's shipped 1.2 slave.
`python3 tools/driving.py serve` boots under the gdb-stub server with the same options.
The machine is the harness's A500 (68000, 1 MB chip, 2 MB fast); NTSC=1 adds AddMonitor
to the startup-sequence, P6_QUIT_MARKER=1 and P3_HDF_BOOT=1 work as before (`game.sh`). Return skips the opening screens; cursor keys
drive. CTRL-G selects graphics and simulation; changed simulation applies on
next race. Defaults are Normal=10 Hz on 000/010, A2500=20 Hz on 020/030, and
A4000=50 Hz on PAL 040/060. NTSC 040/060 retain A2500. A valid saved
`data/4DPhysics.cfg` choice overrides defaults. A4000 remains experimental.
Numeric `*` quits WHDLoad. CUSTOM2=0 uses original rendering, 1 all optimizations,
2 Fast-RAM renderer alone. CUSTOM3=1 restores original timing and its hook bytes.
Only CUSTOM2 bit 0 appears in the splash: "Enhanced framerate (68020+Fast for
CPU renderer)". Other options remain advanced tooltypes. Credits include
"Enhancements by Vesuri"; current version is 2.0b (13.10.2026).

## Validation and measurements

The current production SHA256 is
`aa17dd5743f016396510d001fb66a03a923f7ae03743f74a0e39ca722dddcc55`
(37440 bytes). The engine and skid loops no longer click: every `ameng1.vce`
sample starts with 4 non-waveform bytes, and `sound_loop_patch` plus two
`PL_W` (code $422, $438) loop ENGI, SKID and SKI2 from byte 4 to the sample end
(ENGI keeps 16 whole periods). A race-start recording on a1200-040 counted clicks
(steps over 12x the local step) idle 22 -> 3, accelerating 14 -> 0, coasting
4 -> 3 at unchanged RMS; the skid loops are checked from the data only. The DSI intro flicker is fixed: its buffer swap now waits for
VBL before the next frame can reuse the old front bitmap. The racing pipeline
is unchanged. `tmp/prof/intro-fix-validation.json` records 250-field before/after
captures for original and enhanced rendering, 47/50 -> 0/50 premature reuse,
five CPU gameplay rows, replay state equivalence, legacy bytes and hook audit.
The ReadMe has a concise user-facing fix entry under 2.0b (13.10.2026).

Simulation/history/replay buffers remain allocated at startup; historical
workspace validation is `tmp/prof/runtime-workspace/validation.json`. Buffer
symbols contain pointers; older snapshot analyzers must dereference them.
Large completed memory captures are losslessly gzip-compressed. The obsolete
large intro instruction trace was removed after retaining compact DMA evidence
and the new complete before/after captures.
CPU default-selection validation remains in `tmp/prof/default-040060`.
P6 measurement SHA: `522d97c2ce16e91c2a4edda5078aed1d86688cc9b7774e58f4bcef0edc690cef`.
The prior splash-only build and screenshot remain in `tmp/prof/splash-v13b`.
Final matrix: `tmp/prof/p6-default-matrix.json`; individual
captures `tmp/prof/p6-default-c{0,1}/{A,A-fast,B,B-fast,C,C-fast,D,D-fast,E,E-fast}`.
The tracked plan retains the FPS tables; the ReadMe gives user options and a concise changelog.
These are emulator measurements, not hardware predictions.

All benchmark cells use frame anchors, a 180-second watchdog and port >=2471.
They close their owned emulator, checking cwd before cleanup. Never kill a
sibling project's FS-UAE. Never request A2500 on A500.

For the calibrated timing environment:

```sh
. tools/env.sh
export FSUAE="$PWD/tmp/contact-write-fsuae/fs-uae"
export FSUAE_NATIVE_PROFILE_SHA256="$(shasum -a 256 "$FSUAE" | cut -d ' ' -f 1)"
BENCH_CYCLE_EXACT=1 BENCH_SIMULATION=20 BENCH_WHD_ARGS='CUSTOM2=1' \
  tools/bench_matrix.sh tmp/build/4DSportsDriving.slave tmp/prof/my-test A A-fast B
```

Use a fresh output path. Cell C additionally needs `P3_HDF_BOOT=1 BENCH_NOMMU=1
P3_REQUIRE_DCACHE=1` and `BENCH_EXTRA_SCRIPT=tools/p6_matrix_check.py` for actual
030 data-cache-on coverage. D/E timing uses calibrated 25/50 MHz, MMU off and
no emulated data cache. `tmp/p6-matrix-run.sh` records the complete release recipe.
`tools/bench_matrix.sh --collect OUTPUT CAPTURE...` verifies frozen binaries and
collects completed results without rerunning them. Short consumed-step windows
include queue-boundary catch-up; use clock funding and sufficiently long windows
for timing claims. Do not confuse copper-switch FPS with DMA pixel equivalence.

The MMU functional capture is `tmp/prof/p6-mmu-fixed/D`: full 68040, native IDE,
matching A1200 motherboard/ROM, JIT off, no NoMMU option. `mmu-check.json` and
`whdl_register.txt` prove gameplay, preference disk load/save/CRC, normal quit,
shell continuation, TC=8000 and CACR=80008000. It is not an FPS result.
`tmp/prof/p6-legacy/B` proves 38 original hook ranges with CUSTOM2=0/CUSTOM3=1.
`tmp/build/p6-hook-audit.txt` audits all hooks, relocation and branch targets.

P5 long lifecycle evidence remains in `tmp/prof/p5-acceptance/{D,E}`. It includes
water crash, restart and finish, but uses a scenery-cleared/water fixture and
idle/menu time; it is not two minutes of continuous stock-track driving.
P6 does not change physics handling, renderer algorithms or replay ABI9.
Native replay evidence: `tmp/prof/p6-native-replay-final/state-check.json`:
both rates play all 301 steps and match all 1120 legacy state bytes at step 200.
A4000 performance matrix: `tmp/prof/p6-a4000-matrix.json` (8 rows).
All 28 matrix rows were checked against the exact P6 measurement SHA above.
PAL opponent replay: `tmp/prof/p6-route-replay/B/route-replay-check.json` proves
all 1510 semantic bytes at steps 1500/1550/1600 and 1802 recorded route bytes.
NTSC: `tmp/prof/p6-ntsc/B-menu-fixed/ntsc-check.json` proves saved-50 fallback,
actual A4000 menu selection rejection, tagged replay rejection and 30-second
native timing (19.964129 consumed steps/s; race-clock ratio 0.99820645).
The earlier NTSC attempts exposed controller/window-quantization issues and
are not acceptance evidence. Their screenshots and logs remain for diagnosis.

## Archive and research history

`make dist` repacks JOTD's installer archive (`4DSportsDriving.lha`) with the
production slave, `release/ReadMe`, `release/Install` (which writes CUSTOM2=1 into the
installed icon) and the assembled source (`release/release.json`), into the repository's
`dist/` as `4DSportsDrivingEnhanced-<version>-<date>.lha`. The fork harness's
`tools/package_testing.py`, which repacked the pre-installed Retroplay archive into
`dist/4DSportsDriving_v2.0b_1461.lha` (926691 bytes, SHA256
`9dd3ba4058c88fb7945852eedf6c20e39c1630765f6ce85b1e12be415167fb06`, a local testing
archive of the cleaned PR build), is retired: a release here is the installer package.

Historical notes are preserved in the fork harness's local Git repository
(`tmp/dev/docs/.git` in the fork worktree, no remote), which was not imported. Its
commit `9311a53` holds the 29 original notes (`simulation-inventory.md`,
`simulation-plan.md`, ...).

## Disk cleanup (2026-10-12)

Removed 49 obsolete raw profiling traces after retaining their analysis
reports, and losslessly compressed 3446 historical snapshots/listings.
Each gzip copy was decompressed and SHA256-compared before removing the
uncompressed original. About 16.8 GiB was freed (project: 23.6 to 6.8 GiB).
Full inventory: `tmp/space-cleanup-manifest.json`.

Current build/archive, P6/current-default captures, replay oracles/fixtures,
original game pack and emulator repositories are preserved. Historical tools
may need their input restored first with `gzip -dk path/to/memory.bin.gz`
(or `slave.lst.gz`). Raw traces listed as deleted must be recaptured if
instruction-level analysis is needed again; reports and source remain.
