# Driving-control regression (2026-10-14)

RC1 (`60123fd26a8c188925c2213118f417e233ad0f883224372e87feeda477e2a836`)
fails ordinary right-button acceleration from rest on the 20 ms player path.
The user reported the same failure with a clutch launch on A1200/68040 40 MHz,
MMU, 32 MiB Fast. The normal icon accelerates correctly.

## Cause and correction

After the native 100 ms acceleration proposal, scalar speed is converted to
20 ms. In the reproduced F3 launch, the native proposal is 12, converted to
2.4. The native vector response returns a nonzero proposal (10 in the trace).
The subsequent integrated velocity is nevertheless erased by the redundant
sub-4 cutoff in `FF1SpeedFromVelocity020`. This repeats every update.

Remove that cutoff from the integrated velocity magnitude. Retain the native
proposal's stop decision and its `velocity_6e2a4` reset, the exact fractional
magnitude, bounds/error checks and 500 speed cap. There is no throttle-dependent
exception, forced minimum speed, input remapping or change to opponents, the
100/200 ms paths, or CUSTOM2=0.

Corrected candidate: 260276 bytes,
`e57c42ec5160f1771146045f81a31c59ff7942f30678e801fb5c00178dd2910d`.

## Evidence so far

Actual native input, 020+Fast F3 demo takeover, throttle applied after countdown:
player speed 0 -> 124; coast -> 113; brake -> 7 -> 0; idle remains 0;
right-button restart -> 103. Both mouse directions reach the native steering
state. All sampled engine errors are zero. Positions advance with speed.
These are behavioral checks, not matched elapsed-time speed comparisons.
Evidence: ignored `tmp/dev/tmp/step5/c4-q03-controls-a1200-fast-fixed-green/`.
The before/after trace is in `c4-q03-drive-check-a1200-fast-trace-green-20261014`
and `c4-q03-drive-check-a1200-fast-trace-green-fix-20261014` under the same folder.

The previous Monaco launch acceptance was invalid: `$2275a` is a 16-bit player
speed followed by the opponent's 16-bit speed, not a 32-bit player speed.
The internal gear value 1 alone does not establish neutral: the original also
accelerates with this value. Do not use either inference as acceptance.

The 1,111 native 68020 scalar-feedback cases pass, including sub-4 fractional
values, signed components/remainders, bounds and invalid-input rejection.
Evidence: `tmp/dev/tmp/step5/drive-speed-feedback-a1200/result.json`.

Further control/configuration checks and replacement archive are in progress.
