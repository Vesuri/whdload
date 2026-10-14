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

## Acceptance evidence

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

Native F1/Fiorano menu selection also passes: control and difficulty both 1;
clutch revs at rest; right Alt changes gear 1 -> 2 once, left Alt returns 2 -> 1;
clutch release launches to speed 130; braking reaches 52 -> 0; right-button-only
restart reaches 103. Engine errors remain zero. Evidence:
`tmp/dev/tmp/step5/c4-q03-drive-manual-a1200-fast-fixed/result.json`.

Legacy control comparison passes after braking out the inherited demo momentum:
right accelerates, release coasts, left stops completely, idle remains stopped,
right restarts and both steering directions reach the same native input state.
Do not compare the raw speed numbers as equal-simulation-time measurements.
Evidence: `c4-q03-controls-legacy-a1200-fast-legacy-rested/result.json`.

An equal-size, RNG-controlled 100-update demo comparison passes all 27 canonical
game-state blocks and all recorded private physics state byte-for-byte. Both
arms report zero errors. Evidence: `c4-q03-drive-state-production-a1200-fast-old`
and `c4-q03-drive-state-production-a1200-fast-fixed`. The helper's intended
low-speed difference is covered by the launch and scalar tests, not hidden by
this high-speed fixture. The production host, 68000 and chip-only 020 payloads
are byte-identical to RC1; CUSTOM2=0 executes unchanged code.

The untraced 020+Fast timing check passes: 60 simulated seconds in 60.035565
emulated seconds (0.05924% error), 13.22979 FPS across 300 presentations, zero
engine errors. This is an uncontrolled demo timing observation, not a matched
speedup claim. Evidence: `c4-q03-drive-timing-a1200-fast-fixed/result.json`.

The reported configuration also passes native controls: A1200, requested
68040/40 MHz, MMU enabled (TC=8000 verified), 2 MiB Chip and 32 MiB Zorro III
Fast. Both buttons produce 9000 RPM at rest; releasing left launches to speed
224 with advancing position. Coasting reaches 212, braking 110 -> 9 -> 0;
released idle stays at zero, right-only restart reaches 99, and both steering
directions are received. All sampled errors are zero. This is a functional
emulator check in warp, not a physical 40 MHz timing claim. Evidence:
`c4-q03-controls-a1200-fast-fixed-040-mmu-32m-controls/result.json`.

An independent corrected-source rebuild is byte-identical. RC2 replaces RC1
for driving acceptance. Historical RC1 performance/frame qualification retains
its original hash and scope; it is not represented as a full rerun on RC2.
Complete human races and real Amiga hardware testing remain deferred.

Harness failures before this passing run were not game failures: a duplicate
SplashDelay argument prevented WHDLoad startup; the first Z3 dump used the wrong
bank address; another emulator lacked native-input monitor support. The passing
run uses one splash option, maps Z3 at $40000000 and delivers actual native input.
No game-state writes force throttle, gear, speed, or demo takeover.
