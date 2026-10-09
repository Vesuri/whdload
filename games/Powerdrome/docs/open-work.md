# Open work

## Current state

Initial bring-up is working. Original slave source reconstructed and byte-identical build
verified. The A500-equivalent boot reaches menus, pits and a moving cockpit. A ten-field pit
trace verifies instruction PCs and full-field cycle accounting. No optimization is applied.

## Ordered next work

1. Establish the automatic demo route and its first racing frame; distinguish it from practice.
   Capture two fresh boots at the same state anchor and compare state, pictures and instructions.
2. Validate racing frame completion (`$8056` is a candidate) against display changes and a
   read-only breakpoint counter. Do not count menu/pit updates as racing frames.
3. Capture fixed-window A500-equivalent and 68020 baselines; attribute CPU, waits, DMA and IRQs.
4. Complete the timing/state map. The CIA TOD clock and frame-delta clamp are found statically;
   measure their behavior across CPUs and under deliberately slower drawing.
5. Build the development slave on WHDLoad 20 KickEmu, retaining original behavior and gated
   VERIFY fixtures. Compare its fixed-window state with the byte-identical reference.
6. Present measured candidates and the timing verdict for the user's design choice, as the
   playbook requires. No performance patch should precede that decision.

The project is **not yet ready to optimize** under the playbook's definition: deterministic
race capture, validated FPS, cross-CPU baselines and the measured coupling model remain open.
