# Where this comes from

This game's history is the `4dsportsdriving` branch of the JOTD fork
(Vesuri/jotd_whdload_slaves), the full development history and verification source
(86b353f there), imported here; its ignored harness (`tmp/dev`) became `tools/` and `docs/`.
Commit hashes in these docs are the fork branch's. The fork's `4dsportsdriving-merge`
holds the cleaned production source in one commit (060c1dc), submitted upstream as PR #36
(PR #26 is superseded and closed); upstream has not merged it.

The release here is built from this development source: `make slave` gives the
production SHA256 below (38788 bytes). The cleaned PR build is a different binary
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

The release is 4D Sports Driving Enhanced 2.0b (10.11.2026), a beta: `make dist` packages
it, and the installed icon enables Enhanced framerate (CUSTOM2=1). Its evidence is
emulator measurement only; no real-hardware play-test is recorded.

## Open

- **Green band in the replay** (tester report, Amiga Forever A4000/40): a light-green
  ground band, dark-green strip under it, flickers over the ramp road in the F3 chase
  camera. Not reproduced on `a1200-040`; the chase camera's Y moves smoothly through
  the hilltop. Needs the tester's .rpl and whether `CUSTOM2=0` shows it.
- **A skid sound at replay restart**: after playing a replay that skids later on and
  pressing ||< then play, the skid loop plays on channel 2 for about 1.5 s from the
  start, where the car only accelerates; the first playback from the same start has
  none. Also with `CUSTOM3=1` (native timing), so it is the game's own sound state
  carried over the rewind (its sound records queue at 1334(a4), consumer h0:7984). Not
  checked against JOTD's slave; not reported by the user.

## P7 integrated

P7 is complete under the user's accepted experimental27/29 decision. Both screened
A4000 changes are integrated for both cars, without tuning. All795 live body records
match the offline candidate in each start position. CommonY1442 and commonSpeed7719
remain failed; commonPitch11 passes. Phase failures are53/70/69. Criteria unchanged.

Replay ABI 11 (the mouse hold input below) loads ABI 10 too and rejects older A4000
recordings; slaves before it reject ABI 11. Fresh save/load matches1510 semantic
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
"Enhancements by Vesuri"; current version is 2.0b (10.11.2026).

## Validation and measurements

The current production SHA256 is
`92ee48d366ce01d36b0e88e4f4bb117989011b8d32cbab0ba99699abf6687b4d` (38788 bytes).
No one-shot leaves its sample as Paula's reload any more. Paula reloads AUDxLC/AUDxLEN
at the end of every sample (Hardware Reference Manual, audio), and both of the game's
drivers stop a one-shot only at its second audio interrupt, after the sample has been
reloaded. Stopped channels' DMA was found on again with no new note: the title music
driver's state 0 (stopped) with DMA on for up to ~120 fields while its tick
(h0:28550) restores the volume. The writer was not identified (candidates: the
kickemu Kickstart 1.3 audio.device, which writes DMACON from its unit state, and
WHDLoad's OS switches; the slave writes no audio DMA bits). Whatever turns DMA on, the
reload is now a 256-byte zeroed chip buffer (allocated at install). It is set at the
first interrupt of a one-shot (music h0:28184; race/replay h0:1b262, 1b28e, 1b2ba,
1b2e6) and at every stop of the race/replay driver (h0:1b434, 1b448, 1b45c, 1b470,
1b48a). Loops are unchanged. With it the user found the title/menu bass drum whine
gone and could no longer reproduce the replay-start right-channel whine (play a while,
then ||<). A stopped channel must also go idle. With its DMA off, Paula ends a word and
goes idle only if the channel's interrupt request is still pending (FS-UAE `audio.cpp`
state 3, `isirq`); otherwise it requests one and replays the same word. The race
driver's handler acknowledges every audio interrupt, so a stopped skid loop kept
replaying its last word at the skid period (~4 kHz): silent at volume 0, a whine at the
volume the CIA sound tick (h0:6f8) writes while the game still marks the skid playing
(between h0:e0c's stop and h0:e16). The user heard it holding a corner at the skid
edge, where the skid starts and stops every few steps. Its own starts get away with it
because they write period 1 first. Every stop now disables the channel's interrupt
(h0:1b434..1b470, 1b48a) and every start clears the request and enables it again just
before DMA (h0:1b57a, 1b5e6, 1b652, 1b6be), as the driver's install does. Counted by an
`SFX_COUNT` build (`make build BUILD=sfxcount VASM_EXTRA=-DSFX_COUNT=1`, counters at
`sfx_idle_irqs`) in an A4000 race on `a1200-040`, mouse ramped into a corner and held at
the skid edge (about 30 skid stops): channel 2 took 33341 interrupts while stopped
before, 32 after. Neither run's recording had sound on that channel while stopped
(volume 0 there), and the skid still starts and loops. Replay playback
staged 300 CPU frames in 300 fields both before and after the replay panel fix (a1200-040,
race with a skid, ||< then play), so the frame rate did not measurably drop.
Mouse steering (`src/mouse_steering.s`) was coarse for two reasons. The target angle
came from (x-160)/2 into the table at -$7514(a4), whose first 7 entries are 0: 56
mouse counts of dead zone, then 1 unit per 8 counts. Then h0:9020 pressed right only
when the target was a whole step (the car table's byte 1, 1..8 units by speed, x4 when
countersteering) past the wheel, else neutral, which centres by twice the step while
moving. Small targets never steered, larger ones gave a sawtooth below them. Now the
target comes from the raw counter with no dead zone, interpolated between table
entries (limit still 127). h0:9020 is replaced by a choice of whichever of right,
left or neutral leaves the wheel nearest the target (at 50 Hz with the two-fifths
step), carrying the remaining error into the next step (bounded by the larger gap
between outcomes). In A4000 mode the wheel can also hold still: input bit 6 with no
steering bits (unused by the game, which reads bits 0-1 at h0:f430, 2-3 at h0:e81e, 4-5
at h0:f144) keeps the wheel and its fraction (`sim_a4000_steering`), and the decision
holds whenever that is nearer the target than any move, carrying no error. Neutral
stays neutral when it equals holding, so no input byte turns nonzero at rest (h0:e606).
The same ramp in A4000 mode now steps 2, 4, ... 14 and holds each, instead of
swinging between 10 and 16 for a target of about 13.5; coming back it holds up to
about half a centring step (2-3 units of 240) before centring. That error is the only state kept; it is cleared when the
game centres the mouse (h0:8ffc: race start, M, around its dialogs) and whenever
the history slot is not the one after the last decision (restart, replay, keyboard
steps). A run left race 1 with error -9; the race entered from the main menu started at 0. Patches: h0:7b08 (native sampler, `CUSTOM3=1`), the field sampler
in `simulation_schedule.s`, h0:9020 and h0:8ffc. Only the recorded left/right bits change, so
replays and the simulation are unchanged. In a race with the throttle held and the
mouse moved right 2 counts every 2 fields to 100 counts, the old slave left the wheel
at 0 throughout (once 1) in A4000 mode. The new one followed from about 20 counts,
averaging about 12 at 100 counts (target 13.5), and returned to 0 at the centre.
A2500 (`a1200-030`) and `CUSTOM3=1` follow too, dithering a step or two around the
target (5/15/20 for a target of about 13), the finest the recorded bits allow there.
Hook audit passes.
The CPU renderer draws a line only inside a staged frame, the plain `$bca` line, and
only within the band it copies back; fills only in the game's set/clear mode
(`$dfc`/`$d0c`). Lines straight into chip RAM had left the replay panel's selection
frames in one display buffer only (stray pixels, striped buttons, flickering edges);
the game's line core also draws AND, OR and XOR lines (h0:2cd88, 2cd9e, 2cdb4), and
its fills have the same modes (h0:2a9ae..2aace). Panel navigation on `a1200-040`
compared both display buffers: damaged in every `CUSTOM2=1`/`2` run before, clean in
3/3 after; `CUSTOM2=0` clean. A race plus replay route had 2 fallbacks before and after.
The engine and skid loops no longer click: every `ameng1.vce`
sample starts with 4 non-waveform bytes, and `sound_loop_patch` plus two
`PL_W` (code $422, $438) loop ENGI, SKID and SKI2 from byte 4 to the sample end
(ENGI keeps 16 whole periods). A race-start recording on a1200-040 counted clicks
(steps over 12x the local step) idle 22 -> 3, accelerating 14 -> 0, coasting
4 -> 3 at unchanged RMS; the skid loops are checked from the data only. The DSI intro flicker is fixed: its buffer swap now waits for
VBL before the next frame can reuse the old front bitmap. The racing pipeline
is unchanged. `tmp/prof/intro-fix-validation.json` records 250-field before/after
captures for original and enhanced rendering, 47/50 -> 0/50 premature reuse,
five CPU gameplay rows, replay state equivalence, legacy bytes and hook audit.
The ReadMe has a concise user-facing fix entry under 2.0b (10.11.2026).

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
