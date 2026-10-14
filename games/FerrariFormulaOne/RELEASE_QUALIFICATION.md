# Release qualification

Emulator qualification is in progress. Human playtesting and real Amiga hardware
testing are deferred by the user. The production build remains unchanged and
opt-in; this document does not declare it release-qualified.

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
`tmp/dev/manifest/release-accelerated-enabled.json`; clock validation is in
`tmp/dev/manifest/release-clock-calibration.json`.

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

Evidence: `tmp/dev/manifest/release-cache-mmu.json` and the frame section of
`tmp/dev/manifest/release-exact.json`. Simulation-state acceptance also passes: nine accelerated/cache cases each
match all 27 recorded state blocks and the complete captured private fractions
for 100 consecutive updates, with zero engine errors. The reference is the
previously accepted algorithm at the same allocation layout: one 030 reference
and one 040 reference; 040 at both speeds and 060 have identical recorded states.
No extra pointer normalization or byte masks were introduced. An exploratory
4 MiB-versus-8 MiB comparison is not an acceptance test because dynamic pointers
and a DOS file handle relocate.

## Runtime and memory checks in progress

Official WHDLoad 17.0 build 5139 passes 20-update functional checks on A500 with
Fast memory, 020 with Fast memory, and 060 with Fast memory. The current shared
runtime is WHDLoad 20.1 build 7190. The slave's required API version remains 17.
On A500 with 512 KiB Chip and 1.5 MiB Slow, 17.0 displays “Can't allocate ExpMem”
before game startup; the same configuration passes with 20.1. Chip-only 020 with 2 MiB Chip passes with 20.0, both with and without ExpChip.
With 20.1 and its default configuration splash, it fails to allocate ExpMem,
including with the older emulator observer. Adding `ConfigDelay=0` passes
20 production updates on the same 2 MiB Chip configuration. The launcher already
sets `SplashDelay=0`; both delays must be disabled for this tested configuration.
This isolates the failure to startup memory pressure rather than game code or
the observer correction. Disabling the configuration splash does not resolve
the 17.0 allocation failure on A500 with 1.5 MiB Slow or chip-only 020.
Use Fast memory for the qualified 17.0 configurations; API compatibility does
not imply identical runtime memory requirements.

With 20.1, A500 with 512 KiB Chip and 2 MiB Fast, without Slow memory, also
passes. The production reservation is 768 KiB expansion memory in addition to
512 KiB Chip, the 260,292-byte slave, and runtime/OS overhead; it is not a claim
that 1.25 MiB total machine memory is sufficient.

Both CUSTOM1 values pass three matched legacy-loop state comparisons on all four
original profiles: A500, A500+Fast, chip-only 020 and 020+Fast. All 26 state
blocks are exact at loops 125/150/175. The 1,005-word union of the three engines'
native patch ledgers also matches in all 24 comparisons, allowing only the
existing timing JSR's relocated host operand. This is the original legacy patch,
not a new performance hook. Equal allocation layout and the established RNG
fixture are applied to both arms. The 020 checks use ConfigDelay=0 with 20.1.
Repeated overlay-load checks remain separate. Evidence:
`tmp/dev/manifest/release-default-c0-validation.json`,
`tmp/dev/manifest/release-default-c1-validation.json` and
`tmp/dev/manifest/release-disabled-ranges.json`.

The normal production build defines FF1_PRODUCTION and excludes VERIFY. No
VERIFY tape or warmup symbols are emitted. Retained diagnostic routine labels
are immediate RTS instructions, and their inactive counter storage stays zero
through the full lap on all three engines. Functional scheduler/installation
state remains necessary. The independent rebuild is still byte-identical.
Evidence: `tmp/dev/manifest/release-production-audit.json`.

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
`tmp/dev/manifest/release-original-observations.json` and
`tmp/dev/manifest/release-accelerated-enabled.json`.

## Native lap completion

All three production paths (A500, chip-only 020 and 020+Fast) complete an actual
player lap crossing in the automatic demo. The completed lap time is copied
exactly to the native last-lap slot; the current lap clock resets to one tenth,
and engine errors remain zero. No guest memory or registers are written by the
debugger. The initial harness incorrectly required an unconditional lap-count
increment: native `$67d5e` tests `$1ed2c` and skips that increment when nonzero.
The demo uses value 12. The corrected test observes this branch condition before
the crossing and verifies its exact counter outcome, rather than suppressing
the check. Evidence: `tmp/dev/manifest/release-laps.json`.

## Additional native controls and system exit

The production A500 build enters Fiorano after a normal track selection and
season reset. Actual modifier-key input with the clutch changes the native gear
state from neutral (1) to first (2), and back to neutral. F1 control and difficulty
fields both read 1; engine errors remain zero. A throttle run consumes fuel,
but its diagnostic checkpoint limit was absent, so it is not a bounded movement
or timing measurement. Native tow returns to the pit.

Actual F10 reaches the WHDLoad abort entry with TDREASON_OK and returns to the
AmigaDOS prompt, confirmed by a screenshot. A 4,190-byte season file was written
through the native requester and retained for a fresh-session load check;
restoration is not yet accepted. Evidence: `tmp/dev/manifest/release-native-ui.json`.

## Open accelerated save/exit case

A fresh 020+Fast session loads the A500 season file and restores F3, but the
subsequent save under a new filename is not persisted. F10 reaches resloadAbort
with TDREASON_OK, then the display remains black. After 10 and 25 host seconds,
the CPU is still in the same system-return loop (observed PCs `$228dee` and
`$228df8`, unchanged A1 `$243478`). The new file is absent from the host drawer.
The emulator was kept alive for the second observation; the failure cannot be
accepted as a completed exit or save round trip. Full memory and register
captures are retained in
`tmp/dev/tmp/step5/c4-q03-release-live-a1200-fast-season-flush/`.

The A500 system return passes. A matching CUSTOM2=0 control is being run to
isolate the accelerated failure before assigning it to the new engine, runtime,
or emulator. Release qualification remains open.

## Remaining acceptance work

- Minimum-memory and minimum/development WHDLoad runtime qualification.
- Both disabled CUSTOM1 variants, including repeated overlay loads.
- F3/F1 controls, Fiorano/Rio/contrasting track, starts/laps, fuel/wear,
  pits, session/results, season save/load, travel/repair clocks; F10 exit passes on A500.
- Final reproducibility and release-candidate documentation.

The Irek executable is unavailable locally; retain its original route and keep
new performance patches gated to SPS 0481, as the plan permits. Enabled NTSC
remains explicitly unsupported. No package has been published.

Local evidence and progress: `tmp/dev/manifest/release-qualification.json`,
`tmp/dev/manifest/release-clock-calibration.json`.
