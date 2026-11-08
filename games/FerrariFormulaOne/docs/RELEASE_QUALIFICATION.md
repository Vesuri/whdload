# Release qualification

**RC1 driving acceptance is withdrawn (2026-10-14).** Human testing exposed a
20 ms player launch regression: ordinary throttle from rest can remain at zero
speed. The demo-based checks below did not establish playable human controls.
The Monaco speed check also incorrectly read two adjacent 16-bit car speeds as
one 32-bit value; it observed an opponent, not player acceleration. Historical
results below remain evidence only for their stated scopes and binary hash.
See [CONTROLS_REGRESSION.md](CONTROLS_REGRESSION.md) for the fix and new checks.
RC2 corrects the launch cutoff and passes native throttle/clutch, coast, braking,
restart, steering and manual gear checks, including the reported 040/MMU/32 MiB
configuration. Its exact binary and test scopes are in that report.
Human full-race playtesting and real Amiga hardware testing remain deferred.

## Current test matrix

From 2.0b on, checks run through the local runner `tools/ff1check.py`
against one build, on WHDLoad 20.1 build 7190. The core profiles are:

- A500 with 512 KiB Chip, 1.5 MiB Slow and 2 MiB Fast
- 020 with 2 MiB Chip and 4 MiB Fast
- cycle-exact 030 at 50 MHz and 040 at 40 MHz, each with 8 MiB Fast

The A500 without Fast memory and the chip-only 020 left the core profiles at FR10
(2026-11-08): the 1 MiB reservation of Fast RAM rendering does not fit them (memory
check below).

Core checks run on every source change: a 20-update smoke on every core
profile, performance-mode FPS (with the share of one-field intervals) and CACR on
the three 020-or-faster profiles, and the exact-state, stable-frame and elapsed-clock
gates on 040. The exact-state gate allows only Fast pointers to differ from the B8-PAL
reference, as the 1 MiB layout moves the guest's Fast allocations.

Feature checks run when a source file they cover changes, and all of them run
for a release:

- memory layouts, the only check that uses several A500 or chip-only setups
- 030 with WHDLoad's MMU option and data cache, and 040 with the MMU
- native lap completion and driving controls
- season save, the race-control route and repair/transport clocks
- CUSTOM2=0 native overlay reloads
- Fast RAM rendering on 030 and 040: the path is active, 50 draws without a fault, and
  both Chip banks equal their Fast shadows

68060 and WHDLoad 17.0 are no longer tested. The slave's cache policy treats
060 as a 040-class CPU. The slave still declares WHDLoad API 17, but only
20.x runtimes are qualified. The sections below record earlier results; any
060 or 17.0 result in them is historical.

## Accelerated clock calibration

The first 030/040/060 measurements must not be used as nominal-frequency FPS
results. The local FS-UAE frequency calculation multiplies two 32-bit values:
`CYCLE_UNIT * baseclock / cpu_frequency`. With PAL baseclock 28,375,160 and
CYCLE_UNIT 512, the intermediate product overflows. At a requested 50 MHz the
reported cpucycleunit was 32 instead of 290.

Widening the multiplication alone is insufficient: `baseclock` is eight times
Chip clock, while `cpucycleunit` consumes units per Chip clock. The widened
intermediate produced 290, corresponding to only about 6.26 MHz of cycle budget.
That interim run is also rejected as a nominal 50 MHz measurement.

The measurement build now uses
`(uae_u64)CYCLE_UNIT * (baseclock / 8) / cpu_frequency`.
Validation passes against the stock 020 multiplier at explicit 14.18758 MHz:
both report unit 128, exactly 284,204 cycles per field, identical complete DMA
rows for all 1,000 fields, and identical starting/ending driving-clock state. At requested
50 MHz, integer unit 36 gives about 50.445 MHz; report that quantization. Do not
infer effective clock directly from the configured frequency or from baseclock.
The original 68000/020 qualification used default clocks, so this explicit-
frequency issue does not invalidate those measurements.

This correction changes the ignored measurement emulator only. The production
slave SHA256 remains
`60123fd26a8c188925c2213118f417e233ad0f883224372e87feeda477e2a836`.
The corrected observer SHA256 is
`e411569ca9e0c30b0cb62b831c88a6dcab4f415517cfcf43fb290d1d5d57171c`.
Corrected accelerated repeats and timing checks pass in the scope below. CPU-instruction
costs unavailable from a core must remain unavailable, never zero-cost claims.

## Accelerated enabled-demo acceptance

The unmodified production build passes on all four accelerated profiles with
2 MiB Chip and 8 MiB Fast, WHDLoad 20.1. Two independent boots per profile have
identical complete 1,000-field DMA observations. All select the 20 ms player /
100 ms opponents path, preserve elapsed-time speed, and report no errors.

| Requested CPU profile | Quantized cycle scale (MHz) | 300-presentation FPS | Elapsed for 60 simulated seconds |
| --- | ---: | ---: | ---: |
| 030-50 | 50.444729 | 16.640136 | 59.975470 s |
| 040-25 | 25.222364 | 16.640136 | 59.975470 s |
| 040-40 | 40.355783 | 16.640136 | 59.975470 s |
| 060-50 | 50.444729 | 16.640136 | 59.975470 s |

Every complete presentation interval is three PAL fields in the measured
windows. The 1,000-field count is 333 changes (16.623497 FPS including window
endpoints); the complete-interval rate is 16.640136 FPS. Clock error is 0.04090%
in each 60-second test. Warp is disabled during measurements.

These are emulator results, not real-hardware measurements or matched speedup
claims against the original release. The 040/060 performance profiles disable
the MMU; functional MMU qualification is separate. Live instruction-cache
readbacks are 0x2011 on 030 and 0x8000 on 040/060. The DMA-only captures provide
no instruction-cost attribution. A separate 20-draw probe on 060 places all
three fields inside drawing, after the observed beam-wait return. There is no
whole-field gap between one draw returning and the next draw starting. This
localizes the ceiling; it does not assign exact CPU costs to individual drawing
routines.

An independent rebuild using the current shared WHDLoad installation reproduces
the accepted 260,292-byte slave and its SHA256 exactly. Evidence is indexed in
`tmp/manifest/release-accelerated-enabled.json`; clock validation is in
`tmp/manifest/release-clock-calibration.json`.

## Cache, MMU and rendered-frame checks

Cache variants pass the 1,000-field enabled-demo test. The 030 with NoCache
records 16.573576 FPS; its complete presentation intervals average 3.009064
fields, with a maximum of four. DCache on 030/040/060 and BranchCache on 060
record 16.623497 FPS in the observation window, with every complete interval
three fields. Live CACR reads verify the requested cache modes.

Separate 040 and 060 MMU-enabled builds each complete 20 production updates
without engine errors. Emulator logs confirm translation enabled (TC=0x8000).
These are functional checks, not MMU-performance measurements.

All ten frame configurations pass: the 020 reference with 8 MiB Fast, the four
accelerated normal profiles, and five cache variants. Each captures 30 complete
RGB frames with the existing matched-state/every-update fixture; fine rendering
uses the same endpoint pose in every arm. Every frame matches the 020 reference,
without pixel masks or debugger memory writes. This validates drawing correctness;
production FPS comes from the unmodified-build measurements above.

Evidence: `tmp/manifest/release-cache-mmu.json` and the frame section of
`tmp/manifest/release-exact.json`. Simulation-state acceptance also passes: nine accelerated/cache cases each
match all 27 recorded state blocks and the complete captured private fractions
for 100 consecutive updates, with zero engine errors. The reference is the
previously accepted algorithm at the same allocation layout: one 030 reference
and one 040 reference; 040 at both speeds and 060 have identical recorded states.
No extra pointer normalization or byte masks were introduced. An exploratory
4 MiB-versus-8 MiB comparison is not an acceptance test because dynamic pointers
and a DOS file handle relocate.

## Qualified runtime and memory configurations

The qualified runtime is WHDLoad 20.1 build 7190. The slave's required API
version remains 17. Historical WHDLoad 17.0 build 5139 checks passed only with
Fast memory (A500, 020 and 060); 17.0 could not allocate ExpMem on A500 with
1.5 MiB Slow or on chip-only 020. Those checks are no longer repeated.
Chip-only 020 with 2 MiB Chip passes with 20.0, both with and without ExpChip.
With 20.1 and its default configuration splash, it fails to allocate ExpMem,
including with the older emulator observer. Adding `ConfigDelay=0` passes
20 production updates on the same 2 MiB Chip configuration. The launcher already
sets `SplashDelay=0`; both delays must be disabled for this tested configuration.
This isolates the failure to startup memory pressure rather than game code or
the observer correction.

From FR10 (2026-11-08) the reservation is 1 MiB for Fast RAM rendering. The memory
check on the FR10 slave `376d1164…`: A500 with 512 KiB Chip and 2 MiB Fast starts; A500
with 512 KiB Chip and 1.5 MiB, 1 MiB or 512 KiB Slow, and the 020 with 2 MiB or 1 MiB
Chip only, do not. The rest of this section describes the earlier 768 KiB reservation.

With 20.1, A500 with 512 KiB Chip and 2 MiB Fast, without Slow memory, also
passes. The production reservation is 768 KiB expansion memory in addition to
512 KiB Chip, the 260,292-byte slave, and runtime/OS overhead; it is not a claim
that 1.25 MiB total machine memory is sufficient.

The tested smaller A500 arrangements (512 KiB Chip plus 512 KiB or 1 MiB
Slow) and the 1 MiB Chip-only 020 do not start successfully. They are excluded
from the qualified configurations. These are bounded startup/functionality
checks, not a universal minimum-memory guarantee or an exhaustive runtime/OS
cross-product.

Both CUSTOM1 values pass three matched legacy-loop state comparisons on all four
original profiles: A500, A500+Fast, chip-only 020 and 020+Fast. All 26 state
blocks are exact at loops 125/150/175. The 1,005-word union of the three engines'
native patch ledgers also matches in all 24 comparisons, allowing only the
existing timing JSR's relocated host operand. This is the original legacy patch,
not a new performance hook. Equal allocation layout and the established RNG
fixture are applied to both arms. The 020 checks use ConfigDelay=0 with 20.1.
Repeated overlay-load checks remain separate. Evidence:
`tmp/manifest/release-default-c0-validation.json`,
`tmp/manifest/release-default-c1-validation.json` and
`tmp/manifest/release-disabled-ranges.json`.

The normal production build defines FF1_PRODUCTION and excludes VERIFY. No
VERIFY tape or warmup symbols are emitted. Retained diagnostic routine labels
are immediate RTS instructions, and their inactive counter storage stays zero
through the full lap on all three engines. Functional scheduler/installation
state remains necessary. The independent rebuild is still byte-identical.
Evidence: `tmp/manifest/release-production-audit.json`.

## Original release observations on accelerated profiles

The original v1.01 demo was measured separately, with the corrected observer,
warp disabled for each 1,000-field window (20.031887 seconds), after 125 native
updates. These observations are not matched-state speedup comparisons: the
original and converted loops advance different amounts of simulation during the
measurement, and startup RNG is uncontrolled.

| Emulator profile | Original CUSTOM1=0 FPS | Original CUSTOM1=1 FPS | Enabled production FPS |
| --- | ---: | ---: | ---: |
| 030 50 MHz | 5.691 | 7.139 | 16.623 |
| 040 25 MHz | 5.491 | 6.540 | 16.623 |
| 040 40 MHz | 5.491 | 6.540 | 16.623 |
| 060 50 MHz | 5.541 | 6.639 | 16.623 |

The original calendar and session clocks advance only 11.0–11.5 seconds with
CUSTOM1=0, or 13.1–14.3 seconds with CUSTOM1=1, during those 20.032-second
windows. Enabled production independently passes the 60-second elapsed gate
with 0.0409% error. Faster presentation alone therefore understates the behavioral
change: the new mode also keeps simulation time aligned with elapsed time.

The enabled 300-presentation measurement is 16.640 FPS; the table uses its
1,000-field window count for the same observation length as the original.
Quantized emulator clock scales and coarse 040/060 cache charging prevent
hardware speed or CPU-ranking claims. No further accelerated optimization is
required by this qualification task. Evidence:
`tmp/manifest/release-original-observations.json` and
`tmp/manifest/release-accelerated-enabled.json`.

## Native lap completion

All three production paths (A500, chip-only 020 and 020+Fast) complete an actual
player lap crossing in the automatic demo. The completed lap time is copied
exactly to the native last-lap slot; the current lap clock resets to one tenth,
and engine errors remain zero. No guest memory or registers are written by the
debugger. The initial harness incorrectly required an unconditional lap-count
increment: native `$67d5e` tests `$1ed2c` and skips that increment when nonzero.
The demo uses value 12. The corrected test observes this branch condition before
the crossing and verifies its exact counter outcome, rather than suppressing
the check. Evidence: `tmp/manifest/release-laps.json`.

## Additional native controls and system exit

The production A500 build enters Fiorano after a normal track selection and
season reset. Actual modifier-key input with the clutch changes the native gear
state from neutral (1) to first (2), and back to neutral. F1 control and difficulty
fields both read 1; engine errors remain zero. A throttle run consumes fuel,
but its diagnostic checkpoint limit was absent, so it is not a bounded movement
or timing measurement. Native tow returns to the pit.

Actual F10 reaches the WHDLoad abort entry with TDREASON_OK and returns to the
AmigaDOS prompt, confirmed by a screenshot. A 4,190-byte season file was written
through the native requester; its qualified cross-session restoration is below. Evidence: `tmp/manifest/release-native-ui.json`.

## Season persistence and write-cache requirement

Season save/load passes with `NoWriteCache` on the tested 020+Fast emulator.
The A500's 4,190-byte native save is loaded in fresh enabled and legacy sessions,
then saved under a new filename. Both resulting host files are byte-identical,
without exclusions, SHA256
`00afdad9ced97a64879dffa116194bd5480e4c8b6d5a31d68dfb5ca211b5953f`. Actual F10 returns both sessions to the visible
AmigaDOS prompt. Loading restores the saved F3 selection. The native round trip
changes the serialized `curtime` field from 08:02 to 08:04 in both arms; every
other input byte is retained. The acceptance comparison covers both complete
resulting files, including that timestamp.

Without `NoWriteCache`, both enabled and CUSTOM2=0 runs stall in WHDLoad's
file-cache cleanup after the save. The same failure occurs on 20.0 and 20.1.
The saved-file cache entry remains pending and the new host file is absent;
waiting 25 host seconds does not complete the return. Captured instructions
match WHDLoad's own cache-cleanup routine. This is not isolated to the new physics
mode, and no real-hardware or general runtime defect is claimed.

Use `NoWriteCache` for qualified save/load runs on this emulator configuration.
It affects disk buffering, not CPU caches or simulation intervals. Keep this
requirement in candidate launch instructions. The production slave is unchanged.
Evidence: `tmp/manifest/release-season-roundtrip.json`; failing controls and
full memory captures remain available. Reusable guidance is committed to
AmigaXDev `docs/reference/headless-fsuae.md`.

## Disabled native overlay reloads

Both CUSTOM1 values pass on A500, A500+Fast, chip-only 020 and 020+Fast with
CUSTOM2=0. Actual device input leaves driving, returns through the native pit
and race-control screens, selects qualifying, and loads driving again. All
1,005 words in the combined performance patch inventory exactly match the
first load and the original native reference after reload.

For CUSTOM1=0, the original timing callback remains installed; its host address
is checked separately before normalizing that linkage operand. For CUSTOM1=1,
the native six bytes at `$6a304` remain `e34048c02840`. This direct native-code
check complements the earlier RNG-controlled state fixture, whose startup
control deliberately installed a timing callback for both options. An initial
harness assertion incorrectly required that callback for CUSTOM1=1; correcting
it to the original option contract preserves the complete patch-word gate.
Evidence: `tmp/manifest/release-disabled-reloads.json` (eight passing cases).

## Monaco standing start and tow

On the production 020+Fast path, actual native controls select Monaco, F3 and
Race, with the clock set to 12:55 before the 13:00 start. Entering the cockpit
starts a fresh driving epoch. The native countdown falls from 40 to zero; the
red light changes to green. The 501 update checkpoints complete with no engine errors. The original
claim of player acceleration is withdrawn: the 32-bit speed read combined the
stationary player with the moving opponent next to it. The session
clock reaches 6.1 seconds after the countdown; the calendar reaches 13:00:06.3.
These counts are simulation updates, not rendered frames.

Actual tow exits driving and clears the scheduler context before returning to
native results/pit/transport screens. An earlier 13:00 selection reached the
cockpit too late and produced a native DNF; it is retained as a diagnostic and
is not used as start acceptance. Human completion of a race remains deferred.
Evidence: `tmp/manifest/release-monaco.json`, with selection, red-grid and
green-light screenshots and complete state captures.

## Native repair and transport clocks

Production 020+Fast and CUSTOM2=0 pass matched native UI operations on the same
machine/runtime configuration. Changing a tyre compound requests 70 tenths at
menu h176+$eae; both arms advance the calendar by exactly 78 tenths, preserving
the native 13-tenth batching. Monaco-to-Rio transport executes menu
h167+$84..$aa and adds exactly four days in both arms. The game's actual
four-day intercontinental rule is retained, despite the manual's three-day text.

Each complete before/after calendar is checked against its native increment,
including all date and time fields. The session clock and every other captured modal field are
unchanged across each isolated operation. The enabled driving scheduler remains
entirely zero, with no pending driving time or completed updates. These are
native input and read-only breakpoint observations; no debugger state writes
or clock masks are used. Initial calendar times differ between sessions, so this
is an operation-level clock comparison, not a whole-game matched-state replay.
The existing exact-state gates remain unchanged. Evidence:
`tmp/manifest/release-modal-clocks.json`.

## Completion and remaining scope

The emulator release matrix is complete: original-option first loads and native
reloads; base and accelerated CPU paths; cache and functional MMU checks; exact
state and complete frames; elapsed clocks; native laps, F1/F3 controls, Fiorano,
Rio and Monaco routes; starting grid, bounded throttle, pits/tow, pause,
session/results, save/load, repair/transport and F10. Earlier directed contact,
recovery, fuel/wear and grid/dense gates remain attached to the accepted engine
bytes; those are not claims of a complete human-driven race.

The final integrity audit recomputes all nine accelerated state comparisons and
hashes the actual pixels of all 300 retained frame images. Both independent
260,292-byte builds and each payload hash agree. Source and toolchain hashes are
recorded in `tmp/manifest/release-final-artifact-audit.json`.

The local candidate is prepared under `tmp/release/FerrariFormulaOne-1.02-rc1/`
and its sibling ZIP. It contains the slave, launch scripts, build identity and
these qualification notes; no game data, Kickstart, WHDLoad or test fixture is
included. `manifest/release-candidate.json` records package membership and hashes.
Nothing has been published or pushed.

Deferred work is human playtesting, including complete races, and real Amiga
hardware qualification. The unavailable Irek executable retains its original
route and is not runtime-qualified. Enabled NTSC remains explicitly rejected.
The original release's lower memory requirement is not preserved. The tested
save/load configuration requires `NoWriteCache`; chip-only 020 with WHDLoad 20.1
requires `ConfigDelay=0` and `SplashDelay=0`. WHDLoad 17.0 and 68060 are not
tested. C4-T01 micro targets are
optional future optimization; the user-selected matched-workload gate passed.

Local evidence: `tmp/manifest/release-qualification.json`. The existing
exact-state, frame, elapsed and legacy gates have not been weakened.

The final completion audit covers all seven Step-7 requirement groups against
retained captures and package bytes, with no required emulator work remaining.
Its index is `tmp/manifest/release-completion-audit.json`. Human/hardware
work and the permitted version/video limitations above remain explicit.
