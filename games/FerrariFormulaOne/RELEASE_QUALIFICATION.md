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
Corrected accelerated repeats and timing checks are underway. CPU-instruction
costs unavailable from a core must remain unavailable, never zero-cost claims.

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
