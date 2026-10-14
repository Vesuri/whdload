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

The measurement build now widens the multiplication to `uae_u64` before dividing.
A fresh 030 capture verifies cpucycleunit 290 (effective clock 50.096834 MHz due
to integer quantization), 49.9204102 Hz fields, and exactly 1,000 driving-clock
fields during the 1,000-field DMA census. Simulation error remains zero.
The original 68000/020 qualification used default clocks, so this explicit-
frequency overflow does not invalidate those measurements.

This correction changes the ignored measurement emulator only. The production
slave SHA256 remains
`60123fd26a8c188925c2213118f417e233ad0f883224372e87feeda477e2a836`.
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
`tmp/dev/tmp/step5/c4-q03-release-census-030-50-clock-fixed-a/`.
