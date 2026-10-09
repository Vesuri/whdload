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

Follow the [performance implementation plan](performance-plan.md). The selected scope is
planar scene rendering into fast RAM followed by a CPU copy to the chip back buffer, plus
measured drawing-loop improvements. Retain the existing elapsed-time simulation and update
order; a new scheduler, timestep policy or frame cap is outside this work.

1. Repeat the complete Practice capture, validate the driving presentation marker, and capture
   a 68020 baseline. Add fixed-state drawing fixtures and race/effect coverage.
2. Resolve or isolate original/development-slave equivalence, including the legacy Copylock D2
   result. Preserve the current native baseline while providing experimental guest fast memory.
3. Measure CPU fast-to-chip copy and tail-seed costs with the native display active. Keep code,
   scratch and bitmap placement separately controllable so each benefit can be attributed.
4. Prototype a guarded wrapper at `$cee8` using the same four-plane layout in fast RAM.
   Validate full-image equivalence before narrowing this view to rows 19–153, with preservation
   of uncleared rows 150–153. Copy before post-render HUD work and the native presentation.
5. Move audited CPU scratch/code to fast RAM, make span dispatch cache-safe, and optimize
   scanline and edge loops independently. Enable only measured winning machine/path combinations.
6. Complete longer gameplay and accelerated-hardware validation before selecting release defaults.

The existing trace confirms one movement update per scene render, using the stored elapsed-time
delta. Some other operations are per-loop; retain their native behavior. Fast planar staging is
feasible in the identified drawing path, but end-to-end benefit awaits the prototype and A/B
measurements on faster CPUs. The estimated chip data-traffic reduction is not a measured speedup.
