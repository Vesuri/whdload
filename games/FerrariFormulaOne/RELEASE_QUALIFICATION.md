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
no instruction-cost attribution. A render-stage observation is being used to
explain the shared ceiling.

An independent rebuild using the current shared WHDLoad installation reproduces
the accepted 260,292-byte slave and its SHA256 exactly. Evidence is indexed in
`tmp/dev/manifest/release-accelerated-enabled.json`; clock validation is in
`tmp/dev/manifest/release-clock-calibration.json`.

## Remaining acceptance work

- Corrected 030/040/060 comparisons, cache variants and MMU functional checks.
- Minimum-memory and minimum/development WHDLoad runtime qualification.
- Both disabled CUSTOM1 variants, including repeated overlay loads.
- F3/F1 controls, Fiorano/Rio/contrasting track, starts/laps, fuel/wear,
  pits, session/results, season save/load, travel/repair clocks and F10 exit.
- Final reproducibility and release-candidate documentation.

The Irek executable is unavailable locally; retain its original route and keep
new performance patches gated to SPS 0481, as the plan permits. Enabled NTSC
remains explicitly unsupported. No package has been published.

Local evidence and progress: `tmp/dev/manifest/release-qualification.json`,
`tmp/dev/manifest/release-clock-calibration.json`.
