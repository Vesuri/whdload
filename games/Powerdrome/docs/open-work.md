# Open work

## Current state

The original slave is reconstructed and rebuilds byte-identically. The WHDLoad 20 KickEmu
rebase has VERIFY input fixtures for the title demo (`CUSTOM5=1`) and Practice (`CUSTOM5=2`).
Practice uses Enter → native practice-button shortcut → Space, then captures at the first
pit departure animation iteration (`$14764`). A single 500-field A500 trace covers ten nominal
PAL seconds, including the ship leaving the pit, the cockpit transition and track gameplay.
See development for the command, internals for the route, and the
[practice profile](practice-profile.md) for measured phase costs and optimization priorities.
Track edge/span rasterization takes 54.27% of recorded cycles; background filling takes 8.45%.
The optional fast planar renderer is implemented behind `CUSTOM1=1`, off by default.
It stages the normal cockpit scene, copies the validated 21,600-byte extent back to chip
RAM, moves the rasterizer into fast RAM, and replaces hot branch
rewriting with static span loops. The original elapsed-time simulation and presentation
sequence remain intact. See [implementation and verification](performance-implementation.md).

A complete ten-second combined twin run passed 66 completed staged scenes with no pixel,
scratch, register, condition-code or guard failures. Copied code remained unchanged.
Independent 500-field 68020 measurements improved from 15.68 to 22.15 nominal PAL
presentations/s. Bitmap staging alone was approximately break-even; scratch relocation
added negligible benefit and remains a VERIFY experiment. A fresh final-build run reproduced
the full 500-field presentation sequence. The 68000
fast-RAM comparison slowed from 11.32 to 9.35 fps; the option remains off by default.
No-fast-RAM fallback preserved native hook bytes, imagery and frame cadence. These are
emulator results, not real-accelerator performance claims. The complete original Practice
baseline now has an identical 500-field fresh-boot repeat.

The title-demo baseline at revision `02dbc27` has two matching fresh-boot A500 traces and
independently verified frame counts on A500 and 68020 (9.7 and 13.2 demo fps). Those title-demo
figures are separate from the practice launch profile.

## Ordered next work

Follow the [performance implementation plan](performance-plan.md). The selected scope is
planar scene rendering into fast RAM followed by a CPU copy to the chip back buffer, plus
measured drawing-loop improvements. Retain the existing elapsed-time simulation and update
order; a new scheduler, timestep policy or frame cap is outside this work.

1. Extend automated coverage to long races, opponents, all views, collisions, pit re-entry,
   restarts and effects before widening the guarded fast path.
2. Audit remaining game self-modification before enabling caches; test real 68030/040/060
   accelerator memory/cache configurations. CPU type alone is not a bandwidth guarantee.
3. Resolve original/development-slave equivalence, including the legacy Copylock D2 result.
   Current performance comparisons isolate this issue by using the same development loader.
4. Consider further edge/span arithmetic changes only with identical-input comparisons and
   independently measured benefit. Do not introduce a simulation scheduler or frame cap.
