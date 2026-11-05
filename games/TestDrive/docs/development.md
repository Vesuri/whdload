# Test Drive development setup

The slave source is `src/` (`TestDriveHD.s` with `simulation.s`, `render.s`, their patch
lists and the VERIFY-only `simulation-verify.s`); `manifest/source.commit` pins the upstream
commit the work started from. Paths below are relative to the game directory
(`games/TestDrive`), where the harness that lived in the fork's ignored `tmp/dev/` is now
`tools/`, `docs/` and `manifest/`.

`make unpack ARCHIVES=<directory>` installs the two original archives that
`inputs.sha256` pins (also in `manifest/inputs.sha256`) into `tmp/archives/` and unpacks
them: the pristine game is `tmp/game/TestDrive_v1.3_0089/TestDrive/` and the installer
baseline is `tmp/game/TestDrive/TestDriveInstall/`. Preserve both unchanged. The
extracted-file manifests are `manifest/*.files.json`; `tools/check_inputs.py` checks
them with the pinned runtime (`manifest/runtime-inputs.sha256`).

The harness's retained evidence (captures, preserved slaves, the native diagnostic
emulator in `tmp/phase3/native-emulator/`, the local packages in `tmp/dist/`) is
game-derived and stays out of git; it remains in the fork worktree's ignored `tmp/dev/`.
Tools that re-check evidence read it from this game's `tmp/` and `tmp/dist/`, so copy what
a check needs there first. The runtime pins are those of the 2.0b work (WHDLoad 20.0, the
FS-UAE, gdbserve and fsuae_common builds of that time); the shared environment has moved
on since, so tools that call `check_inputs.check()` refuse until the runtime is re-pinned.

From a bash shell, source `tools/env.sh` to load the shared environment
(`../../common/env.sh`) and set `HARNESS_ROOT` (the game directory), `GAME_SOURCE`,
`TD_GAME` (the installed drawer) and `SLAVE_NAME`.
Build with `make slave` and `make verify` (or `tools/build.sh` and
`VERIFY=1 tools/build.sh`): `tmp/build/release/TestDrive.Slave` and
`tmp/build/verify/TestDrive.Slave`, each with its listing `TestDrive.lst`. The build is
the repository's (`game.conf`): vasm with the shared WHDLoad includes, the shared lvo
bridges and `AMIGA_SHARE/ndk/Include_I`; `make check` proves the release build still gives
`release/slaves.sha256`, compiles every tool and runs the static checks that need no
captures (`GAME_CHECKS` in `game.sh`). No build date is embedded: the slave's
`$VER` string carries the fixed release date, `2.0b (13.10.2026)`, which also names the
release archive. `manifest/baseline-source.commit` pins
the original 1.4 source; `manifest/overlay-reference.commit` pins TD2's helper source.

## Harness (phase 1)

The local harness is implemented and acceptance commands/evidence are in
`testing.md`. `internals.md` contains the phase-2 patch/routine inventory, hunk/overlay layout
and the TD-only seed state map.

Run: `make run` boots the release build from a disposable copy of the installed game
(`make run SLAVE=original` the shipped 1.3); SLAVE selects another slave, WHD_ARGS adds
WHDLoad options. The default machine is the harness's A500 (68000, 1 MB chip, 2 MB fast).
Use TD_SETUP=a500, a1200 or a1200-030 for the TD2 reference machines (`game.sh`); SETUP
selects the shared named machines such as a1200-040; do not combine the two selectors.
Every boot saves the effective machine in `tmp/run/<instance>/.run/machine.json`. The
captures that boot their own emulator run as a separate `INSTANCE` named after their
output directory (`tools/private_run.py`), whose `.run` links to that instance's run
directory.

Debug: `TD_SETUP=a500 WARP=1 python3 tools/td.py serve`; when serving, use
`shot`, `wait`, `stop`, `cont`, `gdb`, `until`, `profile` and `quit` from another
shell. `quit` stops only this harness's emulator. The profile command verifies the
pinned emulator. The installed x86 build uses the shared LLDB PC-window fix; the
pinned native diagnostic build has a complete address window without LLDB.

`tools/profile_demo.sh OUT` captures the driving demo with PCs and reports.
`tools/fixed_window.sh OUT [SLAVE]` defaults to the phase-4 first attract race,
100 fields, the retained phase-4 VERIFY slave and CUSTOM3=1. It checks manifest/race-anchor.json and
uses the pinned native emulator. SWAP_ONLY=1 counts publications with breakpoints
for the 68030. ANCHOR=0x18ba selects only the legacy phase-1 VBL diagnostic path.
Captures preserve the exact slave/configuration and refuse an existing output or
active interactive server. Dump paths are relative inside the harness.

Phase 4 is complete: `phase4.md` documents the LoadView marker, h4:$F6 anchor,
VERIFY RNG fixture, two fresh boots per preset and CPU/DMA cost table. Nominal PAL
100-field FPS is 4.0 / 8.5 / 10.0 on a500 / a1200 / a1200-030. The last preset
has no usable instruction trace, so CPU costs remain unavailable. State comparison
has both the legacy seed map/raw mode and the phase-5 physics/score map in
`timing_map.py`; `internals.md` documents its writers and representation.

## Overlay cache flush (phase 6.1)

The public installer and installed-game archives both contain slave 1.3. Their
original filenames and inputs are preserved. The earlier “shipped 1.4” description
was incorrect. The user accepted the unmodified repository-1.4 rebuild as the A/B
baseline; shipped-1.4 binary equivalence is not claimed. It was built before edits
and retained as `tmp/build/TestDrive-1.4-rebuilt.slave` with its listing.

The preserved overlay-only normal slave is 1.5b, still byte-identical to its hardware
handoff. Current builds are 2.0b with phase-8 simulation, phase-9 blitter optimization and phase-10 fractional rendering. Builds use the same pinned SDK/compiler and omit the date. The current separate
VERIFY build includes phase-7/8/10 instruments; it is not in the A/B bundle.
The TD2 helpers were copied from c4d0af5; comparison with the standalone TD2 source
confirmed that its helper fix is absent, so the fork is the correct reference.

`python3 tools/audit_overlay.py` checks the pinned game hash, the six-byte hook
signatures, and every word-aligned direct-branch candidate in the root hunk.
Unload incoming branches: TD:$062EC/$0630A/$06330 -> $06390; load:
TD:$0689E/$068DE -> $06916. No interior targets found. This conservative scan is
not a proof about indirect control flow. `tmp/build/overlay-audit.txt` is the report.

Smoke test from the game directory:

```sh
AMIGA_SETUP=a1200-040 WARP=1 SLAVE="$PWD/tmp/build/release/TestDrive.Slave" python3 tools/td.py serve
# In another shell, while the server is running:
python3 tools/smoke_overlay.py
python3 tools/td.py shot tmp/build/fixed-attract.png
python3 tools/td.py quit
```

The probe asserts installed jumps before using calibrated addresses; if those
assertions fail, resolve the hunk and slave again. It does not write target memory.
It waits for each helper, runs through `_flushcache`, and verifies the displaced
register restores, SP and return PC. Waiting for a full attract cycle can take
several host minutes. `tmp/build/overlay-smoke.txt` contains both RESTORE_OK=1
checks and emulator TC=8000 enabled=1 messages. No profiler timing claim is made.
Screenshots: `baseline-startup.png`, `baseline-attract.png`, `fixed-startup.png`
(driving demo), `fixed-after-wait.png`, `fixed-attract.png`, all in `tmp/build/`.

Both the rebuilt 1.4 baseline and fixed 1.5b booted. Fixed startup, driving demo,
attract cycling and both overlay exits passed on the PAL A1200/68040 25 MHz preset,
2 MB chip / 8 MB fast, MMU enabled, JIT disabled, WHDLoad 20.0. This does not reproduce
or disprove real hardware's stale-cache failure. Normal user quit now passes with
the pinned native-input emulator on this preset: raw key $5D returns WHDLoad to
the AmigaDOS prompt. Its CACR is $80008000 but data-cache emulation is disabled;
this is quit-path coverage only. `td.py quit` is used separately for cleanup.
All extracted input hashes were checked unchanged after the tests.

Hardware handoff: `tmp/dist/TestDrive-overlay-cache-AB.zip`, or the two drawers under
`tmp/dist/overlay-cache-ab/`, each containing `TestDrive.slave`. README.txt gives the
A/B procedure and limitations; SHA256SUMS pins both slaves. Hardware A/B, a player
race and normal quit remain to be confirmed on the user's A1200/68040.

## Static identification (phase 2)

Run `python3 tools/identify_game.py --manifest manifest/phase11-identification.sha256
--out tmp/phase11/identification` with the shared Python. The default manifest
and output retain the historical phase-2 source inventory. Pinned inputs are
checked before parsing. `tmp/phase2/` retains all hunk metadata, the 107 root
JMP entries, two overlay nodes (3 and 20 exports), instruction-aligned excerpts
and the inventory check. The 17 distinct root patch sites are checked, plus all 84 display/optional range declarations
(root and h4, including four mutually exclusive aliases) through `audit_simulation.py`.

Gameplay and Road Drawer live in hunk 4, so root offsets alone are insufficient.
The local inventory always qualifies overlay offsets. The RNG mixes VHPOSR;
two drawing passes are present. The LoadView publication marker is validated in phase 4; exact TD2 road-walker/CPU-span
counterparts remain not found. Identification and the phase-4 baseline are complete;
phase 5 establishes five-field CLI timing with drawing dependencies. The current inventory includes the explicitly
reviewed VERIFY patch sites and source hash. Prior RAM/trace evidence corroborates
tasks, a4 and VBL.

## Gameplay coverage (phase 3)

Complete; see `phase3.md` for real-speed startup, attract and PC traces, all five
cars driven via native debugger keys, crash/recovery, radar stop and gas station.
The diagnostic emulator, exact slave and machine configuration are pinned locally. Host accessibility/window
input is not used.

## Timing and state model (phase 5)

Complete; `phase5.md` records the five-field CLI deadline, 5/6 PAL results clock,
score/average formulas, full selected state map and RNG contexts. Equal-field
A500/A1200 captures diverge because clutch release waits for both rendered
buffers. Road widths and traffic collision origins/lane updates are also written
by drawing code. The revised tracked plan requires rational 2/5 integration and
simulation-owned decisions/geometry; phase 8 is complete as a PAL emulator beta; see `phase8.md` for its scope and evidence.

`timing_capture.py OUT --fields N` records consecutive VBL data/frame snapshots
from the pinned first-race anchor; `timing_late.py` traces after 600 native fields.
Use TD_SETUP, WHD_ARGS=CUSTOM3=1 and the VERIFY SLAVE as documented in phase5.md.
`check_phase5.py` validates retained evidence; it does not boot the emulator.
Event measurements use `timing_control.py`, `timing_crash.py`, `timing_route.py`
and `timing_radar.py` with their separate phase-5 logs. No host-side input is used.

## Always-on fix acceptance (phase 6)

Phase 6 is complete; see `phase6.md`. Phase-3 display review found no
persistent original display defect requiring another patch. The phase-5 drawing
dependencies remain phase-8 enhanced-mode work. Real A1200/68040 A/B is still
deferred at the user’s request and does not block phase 6. The normal slave and
baseline bytes in the handoff are unchanged.

## VERIFY fixture development (phase 7)

The current VERIFY slave includes the phase-7 instruments documented in `phase7.md`.
`verify_capture.py` uses their player-race anchor and native game-side input tape.
`fixed_window.sh` defaults to the retained phase-4 slave for historical baseline
reproduction; it does not silently substitute the new VERIFY build. The preserved normal 1.5b
and deferred hardware A/B pair remain unchanged; current builds are 2.0b.

## Enhanced simulation development (phase 8)

`simulation.s` and `simulation-patches.i` implement CUSTOM2 fixed-time simulation.
Phase 8 is complete as beta 1.6b, validated in PAL emulation. Set `CUSTOM2=1` in
WHDLoad arguments to enable it; the launch-window option label is phase-11 work.
Normal and VERIFY builds write to `tmp/build/`. `phase8.md` documents arithmetic,
clock/geometry ownership, measured handling, acceptance evidence and reproduction.
The preserved 1.5b/1.4 hardware A/B handoff remains unchanged. Phase 8 itself
makes no FPS claim; phase 9 measures interrupt-suppression gains below.
Fractional rendering is implemented in phase 10 below.

## Blitter optimization (phase 9)

Beta 1.7b suppresses unused blitter-finished interrupts under CUSTOM2. Existing
priority behavior is preserved, with the pre-game enable bits restored on
program return. `render.s` is a build dependency. VERIFY C1 bit 3 retains
original interrupts while leaving enhanced simulation active for measurement.
`phase9.md` records paired fixed-window gains on A500/A1200/68030, native helper
checks and normal-build on/off smoke evidence. `check_blitter.py` rechecks the
retained A/B captures; `test_blitter.py` rejects corrupt evidence. Historical
phase-8 acceptance remains pinned to 1.6b; its checker expects that build.

## Fractional rendering (phase 10)

Beta 1.8b adds C2-gated main/mirror lane, camera, slope/crest and traffic
projection, an exact integer-angle sine cache and atomic mountain-heading
interpolation. TD streams road rows; TD2's table layouts and tangent keys do
not apply. `render-patches.i` is an explicit build dependency.

`phase10.md` documents the native representation, 1,421 renderer assertions,
controlled VERIFY zero oracle, geometry/sideways reports and accepted builds.
C1 bit 4 disables only these projection hooks; C5 bits 3/5/6 select the zero
oracle, draw snapshots and renderer assertions. Normal builds omit them.
Two moving A500 samples use 2.875% / 2.877% self cycles. All three same-build
FPS pairs pass with no regression and equal selected gameplay state. Normal
C2-off/on startup/400-field smoke and option-byte checks pass. Evidence and
preserved normal/VERIFY slaves are under `tmp/phase10/`; `accept_render.py`
collects reports and hashes. Real hardware is deferred and NTSC unvalidated.
The original 1.4/1.5b hardware A/B bundle remains unchanged.

## Local release (phase 11)

The 2.0b (13.10.2026) release beta exposes Enhanced framerate. The installer's Normal icon
and the preinstalled launch icon enable C2; optional GlowIcons keep original
defaults. `phase11.md` records full local regression and exact normal/VERIFY
hashes. All five cars, timing, event paths, renderer assertions/models/budgets,
three CPU presets, WHDLoad 19.2/20.0 and native quit pass. Matched normal-demo
FPS counts are separate from the strict same-simulation projection comparison.

`make dist` builds the release archive: the original installer archive with the
release slave, `release/readme`, `release/Install`, `release/TestDrive.inf` (the Normal
icon with CUSTOM2=1) and the source the release build was assembled from
(`release/release.json`, the shared packager). The harness's own packager, which also
built the preinstalled archive and a portable source Makefile under `tmp/dist/2.0b/`, is
replaced by it; the installer archive's other members are byte-identical to that
package's. `tools/accept_release.py` validates the retained 1.8b development captures and packages;
`tmp/phase11/acceptance-manifest.json` pins the accepted material. The earlier
phase-8/9/10 manifests remain historical snapshots of their exact builds.

Real A1200/68040 testing remains deferred, NTSC unvalidated and publication
unauthorized. The original `tmp/dist/overlay-cache-ab/` pair is unchanged. Remaining
work is listed in `open-work.md` (phase 12 and deferred follow-ups).

All post-JOTD changes are released together as 2.0b. Earlier beta labels in
phase documents identify immutable local test snapshots only. The current
ReadMe/Install use the WHDLoad 20 Install Template. See `release-2.0b.md` for
template provenance, installer coverage and version-only binary equivalence.

## Main-view road continuity

Current 2.0b retains lane, curve and bank fractions at the main-view near-plane
transition. `road-shift.md` records the earlier straight-road lane-anchor fix;
`corner-jump.md` records the completed cornering correction and current checks.
Use `corner_capture.py`, `corner_model.py` and `check_corner.py` for the curved
main-view regression. `subunit_geometry.py --lane-seed` remains the earlier
lane-only/zero-oracle model; it does not model the new curve seed. The current
cost comparison is `corner_cost.py`, including shared lane arithmetic and the
additional bank-sine callee. Its 3.195% A500 sample exceeds the former 3% gate;
the documented +0.175 percentage-point correctness-fix exception is explicit.
Previous release packages and hardware A/B binaries are preserved separately.

## Rev counter display

Current 2.0b caps analogue needle positions at the last numbered dial mark in
both framerate modes. Engine RPM and over-rev damage behavior are unchanged.
See `rpm-needle.md` for reproduction, native helper checks and current evidence.
The normal build and local release archives include this correction; the
historical overlay-cache A/B pair remains unchanged.

## Steering reversal visual correction

The current 2.0b removes the immediate key-dependent road bend when alternating
left/right with the wheel near centre. `steer-reversal.md` describes the two
hooks, native-input reproduction, isolated screen-space test and verification.
Only the visual pose changes; the direct-key vehicle response is retained.

## Bend response and close-traffic visibility

Current 2.0b normalizes the original curvature rounding to its five-field time
scale and restores the missing high-word selection in close-car projection.
`handling-collision.md` records the native route comparison, controlled invisible
truck collision and final on/off 68040 checks. Run `tools/check_handling_collision.py`
against retained evidence after sourcing the environment. The current release is
in `tmp/dist/2.0b/`; previous packages are preserved separately.

## Intro drive-away cadence

`tools/intro_cadence.py NAME baseline|release 0|1` measures the first Porsche
accelerating off the left edge, using isolated a1200-040 sessions and read-only
breakpoints. It resolves h3 through its live overlay jump table, rather than
assuming the gameplay overlay address. In `tmp/intro-cadence/comparison.json`,
rebuilt original 1.4 with CACHE and current release with/without CACHE have
identical field/position samples: during movement one update every two PAL
fields (25 updates/s). The initial static phase retains its nine-field wait.
H3:$648 sets the two-field wait; the selected-car drive-away has the
corresponding wait at h3:$1610. No source change is needed. This measures
emulated animation cadence, not host display presentation. Earlier non-final
capture directories are failed setup/address attempts, not timing evidence.
The active user emulator is left untouched.

## Opening audio and current shared presets

Current 2.0b includes the always-on Paula interrupt/one-shot correction in
`audio-repeat.md`; it is verified with both enhancement modes on the 68040.
`tools/audit_audio.py` and `tools/check_audio.py` retain the focused checks.
The runtime launcher pin is updated to the installed AmigaXDev f6544a2 shared
preset change, verified byte-identical to its source. New accelerated launches
use the processor caches: compatible-core instruction cache on 020 and faster,
plus emulated data cache and full+indirect UAE boot ROM on 030/040/060. Explicit
EXTRA_ARGS overrides remain available for comparisons. Historical captures keep
their recorded effective configuration; earlier claims about data cache being
disabled apply only to those captures, not new launches.

## Diagnostic storage

Bulk raw traces/memory snapshots and large emulator logs were removed to reclaim
disk space. `manifest/diagnostic-cleanup.json` records the scope and totals.
Existing JSON summaries, screenshots, tools, pinned inputs and release builds
remain. Historical documentation describing retained raw captures predates this
cleanup: checks that require those raw files must regenerate them first. The
Countach pre-crash code/chip snapshot is retained for the open steering-dot
report. Keep future raw captures bounded and delete them after extracting the
needed summaries and screenshots.
