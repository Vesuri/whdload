# Open work

## Current state

The original slave is reconstructed and rebuilds byte-identically. The WHDLoad 20 KickEmu
rebase and a CUSTOM5-gated VERIFY name-entry fixture reach the moving title demo. Two fresh
A500 captures match CPU, DMA, initial chip memory and active pixels across 100 fields.
Independent breakpoint counters agree with both CPU traces field for field. Title-demo
measurements are 9.7 fps on the A500 configuration and 13.2 fps on the 68020 configuration.
No performance patch is applied. This is a renderer bring-up benchmark, not a racing baseline.

## Ordered next work

1. Build a deterministic full-screen racing route using native input paths, then repeat it
   across fresh boots. The title demo advances a recorded camera per rendered frame.
2. Validate racing frame completion (`$8056` is a candidate) against display changes and an
   independent read-only breakpoint counter. Capture A500 and 68020 racing profiles.
3. Complete the timing/state map. The CIA TOD clock and frame-delta clamp are found statically;
   measure their behavior across CPUs and under deliberately slower drawing.
4. Compare the development slave with the original on a shared route. Audit the legacy
   Copylock D2 result described in internals; boot success does not establish equivalence.
5. Present measured candidates and the timing verdict for the user's design choice, as the
   playbook requires. No performance patch should precede that decision.

Setup is **not yet ready to optimize** under the playbook's definition: deterministic race
capture, validated racing FPS, measured timing coupling and original/rebase equivalence remain.
