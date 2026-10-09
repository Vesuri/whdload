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
No performance patch is applied.

The title-demo baseline at revision `02dbc27` has two matching fresh-boot A500 traces and
independently verified frame counts on A500 and 68020 (9.7 and 13.2 demo fps). Those title-demo
figures are separate from the practice launch profile.

## Ordered next work

1. Repeat the full Practice capture across fresh boots; compare state, CPU/DMA and screenshots.
   Its first 100 fields already match the earlier short capture on the same build.
2. Validate racing frame completion (`$8056` is a candidate) against display changes and an
   independent breakpoint counter. Separate pit/transition activity from cockpit rendering.
3. Capture the same Practice route on 68020 and complete the timing/state map. Measure the
   CIA TOD clock and clamped frame delta across CPUs and under deliberately slower drawing.
4. Compare the development slave with the original on a shared route. Audit the legacy
   Copylock D2 result described in internals; boot success does not establish equivalence.
5. Present measured candidates and the timing verdict for the user's design choice, as the
   playbook requires. No performance patch should precede that decision.

The requested first in-game ten-second profile is captured. Full optimization readiness still
requires repeated gameplay state comparisons, validated racing FPS and measured timing coupling.
